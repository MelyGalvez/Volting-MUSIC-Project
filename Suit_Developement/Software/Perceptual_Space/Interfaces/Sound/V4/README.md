# Sound_Track — Interactive MIDI Score Navigation

The performer controls musical **time**; the MIDI file provides the
musical **content**. Every validated body movement (a piezo strike, a
fast arm swing) advances the score by exactly one musical instant —
one note or one chord — while sustained voices, program changes,
pedals and pitch bends unfold exactly as written.

```
gesture ──▶ next step        the file decides WHAT sounds
gesture ──▶ next step        the body decides WHEN it sounds
gesture ──▶ ...
gesture ──▶ final cutoff
```

Companion application to `Sound_V2` (direct motion→note mapping) and
`Visual_V2`; independent of both, sharing only the wire protocol
(`PROTOCOL.md`, v2).

## Run

```
pip install -r requirements.txt
python main.py [song.mid]
```

- Windows needs no MIDI package: output uses the built-in Windows
  Multimedia API (the Microsoft GS Wavetable Synth always exists).
  On macOS/Linux, `pip install pygame` for the fallback backend.
- Works **without the suit**: Space / → advance, ← back, Home
  restart, Esc panic. Connect to the `ESP32_Test` WiFi for gestures.
- No MIDI file at hand? `python examples/make_demo.py` writes
  `examples/demo_song.mid`.

Verify an installation headlessly:

```
python main.py --check examples/demo_song.mid
python main.py --list-devices
```

## Triggers

| Source | Movement | Validation |
|---|---|---|
| `piezo_left/right` | stick/hand strike | firmware 1 kHz detector, monotonic hit counters (reboot-safe), velocity from hit peak |
| `swing_left/right` | fast arm raise | Schmitt trigger (35°/20°) + minimum angular speed + refractory, timed by device timestamps |
| keyboard / UI | Space, →, Advance button | fixed strength (`KEYBOARD_STRENGTH`) |

All sources map to actions in `config.GESTURE_MAP` (`advance`,
`back`, `off`). A global 80 ms refractory collapses double triggers
(a strike that also swings the arm). Movement strength shapes note
dynamics (`VELOCITY_MODE`: `file`, `gesture` or `blend`).

## Release modes

- **sustain** (default) — notes ring until the musical position
  passes their written end. Zero clocks: the same gesture sequence
  always produces the identical MIDI output.
- **timed** — written durations are scaled by the performer's
  current pace (estimated from gesture gaps), so staccato stays
  staccato. Switchable live in the UI.

## Architecture

| Package | Role |
|---|---|
| `score/` | immutable preloaded score model + MIDI file loader (mido; chord grouping, tempo map, note pairing) |
| `engine/` | navigation engine (cursor, note ledger, positional releases), release-mode strategies, velocity policies, background ticker |
| `inputs/` | ESP32 polling client, gesture detectors, source→action router |
| `midiout/` | byte-level port backends (winmm / pygame) + musical wrapper |
| `ui/` | Tkinter front-end (pure presentation) |
| `main.py` | composition root, threading, CLI |

Threading: gestures dispatch to the engine directly from the polling
thread (no UI hop); a 2.5 ms ticker executes scheduled releases and
the staleness watchdog; the Tk thread only renders 30 Hz snapshots.
Everything meets behind one engine lock.

Full design rationale, performance data and limitations:
[TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).

## Tests

```
python -m pytest tests
```

80 tests: loader (chords, polyphony, tempo, controls, rejects),
navigation (releases, retriggers, cutoff, jump/back, refractory),
gestures (Schmitt, speed gate, reboots), timed scheduling, MIDI
encoding, and full-piece integration playthroughs in both modes.
