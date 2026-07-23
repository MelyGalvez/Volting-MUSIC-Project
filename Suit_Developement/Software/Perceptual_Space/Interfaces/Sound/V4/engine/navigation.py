# =================================================
# NAVIGATION ENGINE
#
# The heart of Sound_Track: a cursor over the
# preloaded Score. One validated gesture fires one
# Step; the engine owns the complete note lifecycle
# so no note is ever lost or stuck:
#
#   - a ledger of sounding notes keyed by
#     (channel, key), each entry stamped with a
#     generation number so scheduled releases can
#     never kill a newer note on the same key
#   - the deterministic positional release rule:
#     arriving at a step releases every sounding
#     note whose written end the music has passed
#     (this is what preserves polyphony: a whole
#     note keeps ringing across the quarter notes
#     played above it, exactly as written)
#   - a monotonic-time heap for the release mode's
#     scheduled note-offs (timed mode)
#
# Thread safety: every public method takes the one
# internal lock. Callers are the poller thread
# (gestures), the ticker thread (scheduled releases,
# watchdog) and the Tk thread (UI commands); MIDI
# writes are sub-millisecond, so contention is
# negligible at these rates.
# =================================================

import heapq
import threading
import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GestureEvent:
    """
    One validated movement, normalized: where it came
    from, how strong it was (0..1), and when it was
    accepted (time.monotonic()). device_ts carries the
    ESP32 millisecond timestamp when the source has one.
    """

    source: str
    strength: float
    mono: float
    device_ts: int | None = None

    @classmethod
    def now(cls, source, strength):
        return cls(source, strength, time.monotonic())


@dataclass(frozen=True)
class EngineView:
    """
    Immutable snapshot of the engine for the UI thread.
    advance_count changes on every accepted trigger, so
    the UI can flash indicators without callbacks.
    """

    score_name: str | None = None
    total_steps: int = 0
    next_index: int = 0
    finished: bool = False
    suspended: bool = False
    sounding: tuple = ()          # ((channel, key), ...) sorted
    advance_count: int = 0
    last_source: str | None = None
    last_strength: float = 0.0
    mode_name: str = ""
    rate: float | None = None     # timed mode pace, None otherwise
    section: str | None = None    # label context of the last fired step
    next_label: str | None = None # marker on the upcoming step


class NavigationEngine:
    """
    Deterministic score-position engine. All navigation
    entry points (advance / back / jump / restart) silence
    or start notes through the same ledger, so any command
    sequence leaves the MIDI state consistent.
    """

    def __init__(
        self,
        midi_out,
        release_mode,
        velocity_policy,
        *,
        refractory_s=0.08,
        loop_at_end=False,
    ):
        self._midi = midi_out
        self._mode = release_mode
        self._velocity = velocity_policy
        self._refractory = float(refractory_s)
        self._loop = bool(loop_at_end)

        self._lock = threading.RLock()

        self._score = None
        self._next = 0
        self._finished = False
        self._suspended = False

        self._sounding = {}     # (channel, key) -> (Note, generation)
        self._generation = 0
        self._heap = []         # (due_mono, generation, channel, key)

        self._advances = 0
        self._last_advance_mono = -1e9
        self._last_source = None
        self._last_strength = 0.0


# ------------------- Score control -------------------


    def load(self, score):
        """
        Install a new score: silence everything, reset the
        cursor to the first step and emit the file's setup
        state (programs, controllers) so the synthesizer is
        configured before the first gesture.
        """

        with self._lock:
            self._silence_locked()
            self._score = score
            self._jump_locked(0)

    def restart(self):
        with self._lock:
            if self._score is not None:
                self._silence_locked()
                self._jump_locked(0)

    def jump(self, step_index):
        """
        Move the cursor (rehearsal aid). Sounding notes are
        silenced and the control state written before the
        target step (program changes, pedals, bends) is
        replayed so the piece sounds correct from there.
        """

        with self._lock:
            if self._score is None:
                return
            self._silence_locked()
            self._jump_locked(step_index)

    def _jump_locked(self, step_index):
        score = self._score
        step_index = max(0, min(score.total_steps, step_index))

        for event in score.control_state_at(step_index):
            self._send_control(event)

        self._next = step_index
        self._finished = False
        self._suspended = False
        self._mode.reset()


# -------------------- Navigation ---------------------


    def advance(self, gesture):
        """
        The performer's beat. Fires the next step; at the
        end of the piece one extra gesture performs the
        cutoff (releases whatever still sounds, plus the
        file's trailing controls). Returns True when the
        gesture was accepted.

        A refractory window collapses double triggers (a
        strike that also swings the arm, keyboard
        auto-repeat) regardless of their source.
        """

        with self._lock:
            if self._score is None:
                return False

            if gesture.mono - self._last_advance_mono < \
                    self._refractory:
                return False

            if self._next < self._score.total_steps:
                self._fire_locked(
                    self._score.steps[self._next], gesture
                )
            elif not self._finished:
                self._cutoff_locked()
            elif self._loop:
                self._jump_locked(0)
                self._fire_locked(self._score.steps[0], gesture)
            else:
                return False

            self._advances += 1
            self._last_advance_mono = gesture.mono
            self._last_source = gesture.source
            self._last_strength = gesture.strength
            self._suspended = False

            return True

    def back(self):
        """
        Undo one advance: silence, step the cursor back;
        the next gesture replays the step that just sounded.
        """

        with self._lock:
            if self._score is None:
                return
            self._silence_locked()
            self._next = max(0, self._next - 1)
            self._finished = False
            self._mode.reset()


# ------------------- Step execution -------------------


    def _fire_locked(self, step, gesture):
        # 1. Positional releases: everything whose written
        #    end the music has now passed. This scan is
        #    O(polyphony), a few dozen entries at most.
        for slot, (note, _gen) in list(self._sounding.items()):
            if note.end_tick <= step.tick:
                self._off_locked(slot)

        # 2. Channel state written since the previous step
        #    (programs, pedals, bends) — before the notes,
        #    so a same-instant program change applies.
        for event in step.controls:
            self._send_control(event)

        # 3. The chord itself.
        strength = max(0.0, min(1.0, gesture.strength))

        for note in step.notes:
            slot = (note.channel, note.key)

            if slot in self._sounding:
                # Same key restruck while sounding: release
                # first so the synth retriggers cleanly.
                self._off_locked(slot)

            velocity = self._velocity.apply(
                note.velocity, strength
            )
            self._midi.note_on(note.channel, note.key, velocity)

            self._generation += 1
            self._sounding[slot] = (note, self._generation)

        # 4. Scheduled releases requested by the mode.
        for slot, due in self._mode.on_step(step, gesture.mono):
            entry = self._sounding.get(slot)
            if entry is not None:
                heapq.heappush(
                    self._heap,
                    (due, entry[1], slot[0], slot[1]),
                )

        self._next = step.index + 1

    def _cutoff_locked(self):
        self._silence_locked()

        for event in self._score.tail_controls:
            self._send_control(event)

        self._finished = True

    def _send_control(self, event):
        kind = event.kind

        if kind == "program":
            self._midi.program(event.channel, event.data1)
        elif kind == "control":
            self._midi.control(
                event.channel, event.data1, event.data2
            )
        elif kind == "pitchwheel":
            self._midi.pitchwheel(event.channel, event.data1)
        elif kind == "aftertouch":
            self._midi.aftertouch(event.channel, event.data1)
        elif kind == "polytouch":
            self._midi.polytouch(
                event.channel, event.data1, event.data2
            )


# ------------------ Note lifecycle -------------------


    def _off_locked(self, slot):
        entry = self._sounding.pop(slot, None)
        if entry is not None:
            self._midi.note_off(slot[0], slot[1])

    def _silence_locked(self):
        for slot in list(self._sounding):
            self._off_locked(slot)
        self._heap.clear()

    def process(self, now=None):
        """
        Execute due scheduled releases. Called continuously
        by the ticker thread. The generation check makes a
        stale entry (its note already released or restruck)
        a no-op, never a wrong note-off.

        Returns seconds until the next scheduled release,
        or None when nothing is scheduled.
        """

        if now is None:
            now = time.monotonic()

        with self._lock:
            while self._heap and self._heap[0][0] <= now:
                _due, gen, channel, key = heapq.heappop(
                    self._heap
                )
                entry = self._sounding.get((channel, key))

                if entry is not None and entry[1] == gen:
                    self._off_locked((channel, key))

            if self._heap:
                return max(0.0, self._heap[0][0] - now)
            return None


# --------------------- Safety ------------------------


    def suspend(self):
        """
        Silence without losing the score position — used
        when suit data goes stale or the ESP32 leaves the
        running states. The next validated gesture resumes
        exactly where the performance stopped.
        """

        with self._lock:
            if self._sounding or self._heap:
                self._silence_locked()
            self._mode.reset()
            self._suspended = True

    def panic(self):
        """
        Hard stop: ledger silence plus All Sound Off / All
        Notes Off on every channel, for anything a synth
        might still be ringing.
        """

        with self._lock:
            self._silence_locked()
            self._mode.reset()
            self._suspended = True
            self._midi.panic()


# ------------------- Mode switching -------------------


    def set_mode(self, mode):
        """
        Swap the release strategy live. Sounding notes are
        kept (they fall back to the positional rule); the
        pending schedule of the old mode is dropped.
        """

        with self._lock:
            self._heap.clear()
            self._mode = mode
            self._mode.reset()

    @property
    def mode(self):
        return self._mode


# --------------------- Snapshot -----------------------


    def view(self):
        with self._lock:
            score = self._score

            section = None
            next_label = None
            if score is not None:
                if self._next > 0:
                    section = score.steps[self._next - 1].section
                if self._next < score.total_steps:
                    next_label = score.steps[self._next].label

            return EngineView(
                score_name=score.name if score else None,
                total_steps=score.total_steps if score else 0,
                next_index=self._next,
                finished=self._finished,
                suspended=self._suspended,
                sounding=tuple(sorted(self._sounding)),
                advance_count=self._advances,
                last_source=self._last_source,
                last_strength=self._last_strength,
                mode_name=self._mode.name,
                rate=getattr(self._mode, "rate", None),
                section=section,
                next_label=next_label,
            )

    @property
    def score(self):
        with self._lock:
            return self._score
