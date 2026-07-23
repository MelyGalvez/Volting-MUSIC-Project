# Sound_Track — Technical Report

Interactive MIDI navigation engine for the Volting Motion Suit.
Validated body movements advance through a preloaded MIDI score:
the performer controls musical time, the file determines musical
content. New application, built from scratch;
`Arduino_Suit_ESP32_Get_Data_V3`, `Sound_V2` and `Visual_V2` are
untouched.

---

## 1. Concept and requirements

`Sound_V2` maps body angles directly onto notes — the performer
*selects* pitches. Sound_Track inverts the relationship: the piece
is fixed, and each **validated** movement fires the next musical
instant (one note or one chord, called a **step**). Requirements
addressed:

| Requirement | Where it landed |
|---|---|
| Low latency | inline gesture dispatch from the polling thread; winmm output; measured numbers in §6 |
| Robustness | firmware-validated triggers, Schmitt+speed gating, staleness watchdog, reboot handling, note ledger |
| Deterministic behavior | fully preloaded immutable score; positional release rule; device-timestamp gesture detection |
| Clean architecture | five packages with one-way dependencies, strategies for variation points, one composition root |
| Complete MIDI files | chords, cross-step polyphony, tempo map, programs/CC/bends/pedals, markers (§5) |
| Preloaded events | every parse/pair/group/attach step happens at load; playback is array indexing |
| Extensibility | release modes, velocity policies, detectors and MIDI backends are plug-in points (§8) |

## 2. Architecture

```
                    ┌────────────────────────────────────────────┐
                    │                  main.py                    │
                    │   composition root · threading · CLI        │
                    └──┬──────────┬──────────┬──────────┬────────┘
                       │          │          │          │
            ┌──────────▼───┐ ┌────▼─────┐ ┌──▼───────┐ ┌▼─────────┐
   ESP32 ──▶│   inputs/    │ │ engine/  │ │ midiout/ │ │   ui/    │
   HTTP     │ SuitClient   │ │ Navigation│ │ MidiOut  │ │  AppUI   │
            │ detectors    │─▶│  Engine  │─▶│ ports    │ │ (30 Hz   │
            │ GestureRouter│ │ modes    │ │ (winmm/  │ │ snapshot │
            └──────────────┘ │ velocity │ │  pygame) │ │  views)  │
                             └────▲─────┘ └──────────┘ └──────────┘
                                  │
                             ┌────┴─────┐
                             │  score/  │   MIDI file ─▶ immutable
                             │ loader + │   Score at load time
                             │  model   │
                             └──────────┘
```

Dependencies point one way: `ui` and `inputs` know the engine's
public surface; the engine knows the score model and the MidiOut
interface; `score/` and `midiout/` know nothing above them. The
only module that touches the MIDI file format is `score/loader.py`;
the only module that touches a MIDI device API is
`midiout/ports.py`.

### Threading model

| Thread | Period | Work |
|---|---|---|
| suit-client | 10 ms (100 Hz poll) | HTTP poll; on each **new** frame (seq dedup): gesture detection → `engine.advance()` inline |
| ticker | 2.5 ms | `engine.process()` (scheduled note-offs) + staleness/system watchdog |
| Tk main | 33 ms | render `EngineView` snapshots; keyboard triggers; file dialogs |
| loader worker | on demand | parse a MIDI file without freezing the UI |

All state mutation converges on one `RLock` inside
`NavigationEngine`; MIDI writes happen under it and take
microseconds, so contention is negligible at human gesture rates.
The audio path (poll → detect → advance → note-on) never touches
the Tk loop, so a busy or frozen UI cannot delay sound. The
watchdog lives in the ticker thread for the same reason: silencing
stuck notes must not depend on the UI being responsive.

## 3. Implemented modules

### `score/model.py` — immutable score model
`Note` (key, velocity, channel, track, start/end in both ticks and
nominal seconds), `ControlEvent` (program/CC/bend/aftertouch with
semantic fields), `Step` (one navigation unit: simultaneous notes +
channel messages since the previous step + marker label + carried
section), `Score` (steps, setup controls, tail controls, tempo map,
channels, track names) and `Score.control_state_at(index)` —
reconstruction of program/controller/bend state for mid-piece
jumps. Frozen dataclasses; no I/O, no clocks.

### `score/loader.py` — preloading pipeline
1. **Preflight** on the raw SMF header: precise errors for
   non-MIDI data, SMPTE division and format 2 before any parsing.
2. **Merge** all tracks to absolute ticks with provenance
   (track index, file order) — a stable total order.
3. **Tempo map**: piecewise integration of `set_tempo` events;
   tick→seconds is a binary search. Nominal seconds drive chord
   grouping, timed-mode durations and pace estimation.
4. **Note pairing**: note-on/note-off matching per (channel, key)
   with the three real-world edge rules — velocity-0 note-ons are
   offs; a retrigger before the off closes the previous note at
   the retrigger tick; dangling notes close at end of file;
   zero-length notes get a 1-tick minimum.
5. **Chord grouping**: onsets within `CHORD_WINDOW_S` (30 ms) of
   the *group anchor* form one step. Anchoring prevents run-away
   chaining on arpeggiated textures; the window absorbs humanized
   chords from real recordings, which are never tick-exact.
6. **Attachment**: controls at tick ≤ first onset become `setup`
   (emitted at load/restart); controls after the last onset become
   `tail_controls` (emitted at the final cutoff); everything else
   attaches to the step it precedes. Markers/lyrics become step
   labels with a carried `section` for the UI.

mido performs byte-level decoding only (running status, VLQs,
sysex framing); everything musical is done here, and no mido
object survives past load time.

### `engine/navigation.py` — the navigation core
Cursor over `Score.steps` plus the complete note lifecycle:

- **Ledger** `{(channel, key) → (Note, generation)}` — the single
  source of truth for what is sounding. Every note-on registers;
  every path that releases goes through the same `_off_locked`.
- **Positional release rule** (always active): arriving at a step
  releases every sounding note whose `end_tick ≤ step.tick`. This
  is what preserves polyphony *as written*: a whole note keeps
  ringing under four quarters and is released exactly when the
  music passes its end — and it is pure bookkeeping, no clocks.
- **Generation guard**: scheduled releases carry the generation of
  the note they belong to; a stale entry (note already released or
  the key restruck) is a no-op, never a wrong note-off.
- **Navigation**: `advance(gesture)` (fires next step; one extra
  gesture past the last step performs the *cutoff* — releasing
  held voices and emitting trailing controls, like a conductor's
  cutoff), `back()` (silence + replay previous step), `jump(k)`
  (silence + replay accumulated control state so instruments and
  pedals are correct mid-piece), `restart()`, optional loop.
- **Refractory** (80 ms, engine-level): one guard for *all*
  sources against double triggers — a strike that also swings the
  arm, keyboard auto-repeat.
- **Safety**: `suspend()` (silence, keep position — used by the
  watchdog), `panic()` (ledger silence + All Sound Off / All Notes
  Off on all 16 channels + driver reset).
- `view()` returns an immutable `EngineView` snapshot for the UI.

### `engine/modes.py` — release strategies
- `SustainRelease` (default): schedules nothing; the positional
  rule alone ends notes. **Fully deterministic**: the same gesture
  sequence yields byte-identical MIDI output.
- `TimedRelease`: written durations scaled by the performer's pace
  (EMA over file-gap/wall-gap per step, clamped ×0.2–×5), so
  articulation survives slow gestures. The positional rule still
  applies on top — whichever comes first ends the note.

The interface (`reset()`, `on_step(step, now) → release requests`)
is the "additional playback modes" extension point.

### `engine/velocity.py` — dynamics policies
`file` (as written), `gesture` (movement strength alone), `blend`
(default: file velocity scaled 45–100 % by strength — the score's
internal phrasing survives while the performer shapes dynamics).

### `engine/ticker.py`
One daemon thread: scheduled releases at 2.5 ms resolution plus the
watchdog callback. Survives any callback exception.

### `inputs/client.py` — acquisition
Sound_V2's proven poller shape (keep-alive `requests.Session`,
0.5 s timeout, exponential backoff 0.1→1 s, structural validation)
plus frame-edge delivery: `on_frame` fires once per new `seq`, in
the polling thread, so detection latency is not quantized by a UI
tick. Sound_V2 itself remains unmodified.

### `inputs/gestures.py` — movement validation
Pure state machines timed by **device timestamps** (never the wall
clock) — deterministic and replayable given the same frames:

- `PiezoHitDetector`: diffs the firmware's monotonic hit counter;
  counter regression (ESP32 reboot) re-baselines without firing;
  strength from the reported ADC hit peak.
- `SwingDetector`: fires only on an actual crossing of the fire
  plane (35°) from below, with angular speed ≥ 120 °/s, re-arming
  below 20°, per-arm refractory 150 ms. Frame gaps > 250 ms,
  timestamp regressions and > 90° single-frame jumps (heading
  wrap, glitch) *resynchronize* instead of firing. Posture drift,
  slow repositioning and jitter cannot advance the score.

### `inputs/router.py`
Maps detector events to actions via `config.GESTURE_MAP` and gates
on the suit system state (`ready`/`degraded` only — a T-pose during
calibration can never advance). Pure translation, trivially
testable; new input sources are new detectors with new names.

### `midiout/` — output stack
`ports.py`: byte-level backends behind a four-method interface.
`WinMMPort` (ctypes → `winmm.dll`, zero dependencies, µs-scale
writes, driver-level `midiOutReset` for panic) is the Windows
default; `PygamePort` covers other platforms. Device selection by
id, by case-insensitive name substring (e.g. `"loopMIDI"`), or
system default. `output.py`: `MidiOut` — named channel messages,
one lock, full panic. No musical state lives here.

### `ui/app.py` + `main.py`
Tk front-end: file picker, transport (Restart/Back/Advance/Panic),
live release-mode switch, progress bar with step counter and
section labels, sounding-notes display, per-source trigger lamps,
suit/MIDI status bar, keyboard bindings. Pure presentation over
`EngineView` snapshots. `main.py` wires everything, owns thread
lifecycle and teardown ordering, and provides `--check` (headless
device + file verification) and `--list-devices`.

## 4. Key design decisions

1. **The navigation unit is the onset group, not the MIDI event.**
   Grouping at load time (30 ms anchored window) makes "one
   gesture = one musical instant" hold for real-world files, where
   chords are spread by humanization. Navigation itself is then
   just an index increment.

2. **Everything is preloaded; the score is immutable.** Parsing,
   pairing, tempo integration, grouping and control attachment all
   happen once in `load_score`. At performance time there is no
   allocation-heavy work, no searching, no mido objects — and an
   immutable score can be shared across future engines (lanes)
   without defensive copies.

3. **Releases are positional by default.** Tying note ends to the
   *musical position* rather than to timers makes sustain mode a
   pure function of the gesture sequence — reproducible rehearsals,
   testable to byte-identity — while preserving written polyphony
   exactly. Timer-based release is layered on top as a strategy,
   not baked into the core.

4. **The ledger + generation scheme makes note lifecycle airtight.**
   Every code path (positional release, scheduled release,
   retrigger, back/jump/suspend/cutoff) manipulates one dictionary;
   scheduled releases are validated against generations. The
   integration tests assert perfect on/off balance over full pieces
   in both modes.

5. **Gestures dispatch from the polling thread.** The classic
   Tk-tick architecture (Sound_V2) adds up to one UI period of
   latency. Here detection runs the moment a frame arrives and
   calls the (thread-safe) engine directly — the UI merely renders
   snapshots. Measured dispatch cost: ~0.5 ms (§6).

6. **Validation is layered per source.** Piezo strikes are already
   validated by the firmware's 1 kHz detector (protocol v2 hit
   counters — immune to polling rate); the client's job is only
   reboot-safe diffing. Swings need full validation locally:
   Schmitt hysteresis (no boundary flutter), a speed gate (posture
   is not a gesture), crossing-only firing (parked-above jitter is
   inert), refractory, and discontinuity resync. One engine-level
   refractory then arbitrates *across* sources.

7. **Device timestamps for detection, wall clock for arbitration.**
   Detectors are deterministic against the recorded data stream
   (replayable in tests); only cross-source arbitration and timed
   scheduling — inherently wall-clock concepts — use
   `time.monotonic()`.

8. **winmm via ctypes as the Windows backend.** pygame has no
   Python 3.14 wheel (and python-rtmidi none either), so the
   dependency was replaced by the OS API itself behind a port
   interface. This removed a fragile dependency, kept latency at
   the theoretical minimum, and produced the ports-and-adapters
   seam that makes future backends (rtmidi, virtual ports) drop-in.

9. **mido for file decoding only.** Hand-rolling an SMF parser
   adds correctness risk for zero payoff; mido is mature and pure
   Python. It is confined to one function so it can be swapped
   (e.g. for a custom parser or a cached binary format) without
   touching anything else.

10. **Suspend ≠ panic, and the watchdog is not the UI.** Data loss
    silences voices but preserves the cursor (the performance
    resumes where it stopped); the watchdog runs in the 2.5 ms
    ticker so it works even with a frozen window. Keyboard-driven
    use (no suit at all) is deliberately unaffected: the watchdog
    only acts on the healthy→unhealthy *transition*.

## 5. Supported MIDI features

| Feature | Support |
|---|---|
| SMF format 0 / 1 | ✔ (multi-track merge with stable ordering) |
| SMF format 2 | ✘ rejected with a clear message |
| Division | PPQN ✔ · SMPTE ✘ rejected clearly |
| Chords / simultaneous onsets | ✔ one step (30 ms anchored window, configurable) |
| Polyphony / voice overlap / ties across steps | ✔ exact, via positional releases |
| Tempo map (`set_tempo`, mid-piece changes) | ✔ integrated to nominal seconds |
| Note-on velocity 0 as note-off | ✔ |
| Retriggered / dangling / zero-length notes | ✔ deterministic rules (§3 loader) |
| Program changes | ✔ setup + per-step + replay on jump/restart |
| Control changes (pedal CC64, volume, …) | ✔ per-step pass-through; last-value replay on jump |
| Pitch bend | ✔ 14-bit, pass-through + jump replay |
| Channel / poly aftertouch | ✔ pass-through (momentary; not replayed on jump) |
| GM percussion (channel 9) | ✔ passes through; excludable via `CHANNEL_FILTER` |
| Markers / lyrics / track names | ✔ step labels, carried sections, score title |
| Channel / track filters | ✔ at load (`CHANNEL_FILTER`, `TRACK_FILTER`) |
| SysEx | ✘ skipped (see limitations) |
| Velocity | file / gesture-scaled / blend policies |

## 6. Performance

Measured on the target machine (Windows 10, Python 3.14):

| Stage | Measured / budgeted |
|---|---|
| Demo score preload (19 steps, 31 notes, 3 tracks) | 2 ms |
| `advance()` dispatch — detection to note-on handed to winmm | mean 0.50 ms, max 0.64 ms over a real playthrough |
| Scheduled-release resolution (ticker) | ≤ 2.5 ms jitter |
| UI refresh | 30 Hz, decoupled from audio path |

End-to-end trigger latency budget (strike → sound):
firmware piezo confirm ≤ 6 ms (per ENGINEERING_REPORT) + HTTP poll
mean 5 ms at 100 Hz (10 ms worst) + dispatch ~0.5 ms + synth
rendering. **≈ 12 ms typical before the synthesizer**, dominated by
the polling interval — see §8 for the push-transport
recommendation. Swing latency adds one sensor frame (~10 ms) for
the speed derivative.

Complexities: advance is O(chord + polyphony) (a few dozen ops);
positional release scans only the sounding ledger; scheduled
releases are a binary heap; jumps are O(total controls) but occur
only on user navigation. A 10 000-note file preloads to a few MB of
frozen dataclasses; navigation cost does not grow with file size.

## 7. Verification

- **80 automated tests** (`python -m pytest tests`, all passing):
  loader (grouping, pairing edge rules, tempo, attachment, labels,
  filters, rejections), navigation (release order, retriggers,
  cutoff/loop, refractory, back/jump state replay, suspend/panic),
  swing/piezo validation (speed gate, re-arm, refractory, reboots,
  glitches), timed scheduling (pace EMA, clamps, generation guard),
  MIDI byte encoding and panic, plus full-piece integration
  playthroughs in both modes asserting perfect note balance through
  the real loader → engine → port stack driven by the real router.
- **Hardware checks on this machine**: `--check` opens the real
  winmm device and preloads the demo; a headless playthrough drove
  8 steps audibly through the GS Wavetable Synth (latency figures
  above, pace estimator converging to the expected ×1.41); the full
  Tk application ran with the demo loaded and the poller backing
  off cleanly against the absent ESP32.
- Not verified here: gesture thresholds against the physical suit
  (no suit on this network during development) — the values mirror
  Sound_V2's mounting conventions and are config-tunable; and the
  pygame backend (no pygame wheel for Python 3.14 exists yet).

## 8. Remaining limitations

1. **One navigation lane.** The whole mix advances together; the
   architecture anticipates per-track lanes (§9.1) but they are
   not implemented.
2. **SysEx is not forwarded** (GS/GM reset messages, device
   tuning). Files relying on a sysex reset may start with wrong
   synth defaults.
3. **Format 2 and SMPTE-division files are rejected**, not
   converted (both are rare; the error message says what to
   re-export).
4. **Same-tick ordering nuance**: controls attached to a step are
   emitted before its note-ons; a file that interleaves them
   differently at the *same tick* is normalized to this order.
5. **Timed mode is wall-clock dependent** by nature; only sustain
   mode is bit-reproducible.
6. **Aftertouch is not replayed on jumps** (momentary by design);
   a jump into a long note under channel pressure starts neutral.
7. **Polling transport**: worst-case one poll interval (10 ms) of
   trigger latency and sensitivity to WiFi congestion alongside
   Visual_V2 (drop `POLL_HZ` to 50 if sharing the channel).
8. **Swing thresholds are global per arm** (config), not learned
   per performer; a very slow performer may need `min_speed_dps`
   lowered.
9. **Keyboard auto-repeat** is throttled only by the 80 ms
   refractory — holding Space fast-forwards (arguably a rehearsal
   feature, but worth knowing).
10. **UI is deliberately minimal**: no per-track mute toggles, no
    click-to-jump on the progress bar yet (engine `jump()` exists
    and is tested; only the widget binding is missing).

## 9. Recommendations for future work

1. **Multiple lanes (per-track navigation).** Add
   `Score.filter(channels/tracks) → Score` and instantiate one
   `NavigationEngine` per lane over the shared `MidiOut` (already
   thread-safe); map left-side gestures to lane 1, right-side to
   lane 2 in `GESTURE_MAP`. No engine changes required.
2. **Beat-conduct mode.** A `ReleaseMode`-style strategy at the
   navigation level: one gesture = one beat, intra-beat events
   scheduled at the estimated pace through the existing heap +
   ticker. This handles virtuosic passages without one gesture per
   32nd note; the pace estimator and scheduler it needs already
   exist.
3. **AI accompaniment hook.** Emit step-fired events (step index,
   chord, strength, pace) on an observer interface next to
   `EngineView`; an accompanist process can harmonize or drum along
   in real time using the same `MidiOut`.
4. **Live MIDI input as a trigger source.** A detector wrapping a
   MIDI-in port (foot pedal, keyboard) producing `GestureEvent`s —
   the router accepts any source name today.
5. **Push transport.** Replace HTTP polling with a WebSocket or
   UDP stream from the firmware to cut the 5–10 ms polling share of
   the latency budget; only `inputs/client.py` changes.
6. **DAW synchronization.** Emit MIDI clock / Song Position Pointer
   derived from the pace estimator, or Ableton Link, so external
   sequencers follow the performer.
7. **Progress-bar jump + prompter view.** Bind clicks to
   `engine.jump()` (tested); render upcoming steps/labels as a
   scrolling "prompter" — all data is already in the Score.
8. **Performance recording.** Log (gesture time, step, velocity)
   pairs and export the *performed* timing as a new MIDI file —
   pure addition, the data already flows through one place.
9. **SysEx pass-through option** attached to setup/steps for
   synth-reset-dependent files.
10. **Per-song profiles.** A small JSON next to each MIDI file
    overriding config (thresholds, mode, filters), loaded by the
    same worker.
