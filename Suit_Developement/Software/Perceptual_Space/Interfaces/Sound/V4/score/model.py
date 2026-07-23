# =================================================
# SCORE MODEL
#
# Immutable, fully preloaded representation of a
# MIDI piece, organized for navigation: the unit of
# advancement is the Step (all notes striking at
# the same musical instant, i.e. a chord), not the
# raw MIDI event. Everything the engine needs at
# runtime is precomputed here by the loader; nothing
# is parsed, paired or searched during playback.
#
# Pure data: no I/O, no clocks, no mutation.
# =================================================

from dataclasses import dataclass, field


class ScoreError(Exception):
    """
    Raised when a MIDI file cannot be turned into a Score
    (unreadable, unsupported format, or contains no notes).
    Carries a human-readable message.
    """


@dataclass(frozen=True)
class Note:
    """
    One note with its full written lifetime.

    Ticks are absolute file ticks; seconds are the nominal
    file time obtained through the tempo map. Both are kept:
    ticks drive the deterministic release rule (a note ends
    when the musical position passes end_tick), seconds
    drive duration-based release modes and pace estimation.
    """

    key: int           # MIDI note number 0..127
    velocity: int      # written note-on velocity 1..127
    channel: int       # 0..15 (9 = GM percussion)
    track: int         # source track index (future per-track lanes)
    start_tick: int
    end_tick: int      # always > start_tick (loader guarantees)
    start_s: float
    end_s: float

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


@dataclass(frozen=True)
class ControlEvent:
    """
    A non-note channel message (program change, control
    change, pitch bend, aftertouch). Preserved and replayed
    in file order so instrument assignments, pedals and
    expression survive the transfer into gesture time.

    kind/data semantics:
      "program"    data1 = program number, data2 unused
      "control"    data1 = controller,     data2 = value
      "pitchwheel" data1 = 14-bit bend 0..16383 (8192 = center)
      "aftertouch" data1 = pressure,       data2 unused
      "polytouch"  data1 = key,            data2 = pressure
    """

    kind: str
    channel: int
    data1: int
    data2: int
    tick: int
    time_s: float


@dataclass(frozen=True)
class Step:
    """
    One navigation unit: every note starting at (nearly)
    the same musical instant, plus the channel messages
    written since the previous step. One validated gesture
    fires exactly one Step.
    """

    index: int
    tick: int                          # tick of the first onset in the group
    time_s: float                      # nominal file time of that onset
    notes: tuple                       # tuple[Note, ...] sorted (channel, key)
    controls: tuple = ()               # tuple[ControlEvent, ...] in file order
    label: str | None = None           # marker/lyric text at this onset
    section: str | None = None         # last label at or before this step


@dataclass(frozen=True)
class Score:
    """
    A fully preloaded piece. steps is the navigation
    timeline; setup holds the channel messages written
    before the first onset (emitted at load/restart so
    programs and controllers are configured before the
    first gesture); tail_controls holds messages written
    after the last onset (emitted at the final cutoff).
    """

    name: str
    source_path: str
    ticks_per_beat: int
    steps: tuple                       # tuple[Step, ...]
    setup: tuple = ()                  # tuple[ControlEvent, ...]
    tail_controls: tuple = ()          # tuple[ControlEvent, ...]
    tempo_map: tuple = ((0, 500_000),) # ((tick, us_per_beat), ...) ascending
    duration_s: float = 0.0            # nominal file duration
    channels: frozenset = field(default_factory=frozenset)
    track_names: tuple = ()            # tuple[str, ...] by track index

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def note_count(self) -> int:
        return sum(len(s.notes) for s in self.steps)

    def control_state_at(self, step_index: int):
        """
        Reconstruct the channel state (program, controllers,
        pitch bend) in effect just before `step_index`, as a
        list of ControlEvents holding the *last* value of
        each (kind, channel[, controller]).

        Used when jumping into the middle of the piece so a
        program change or sustain pedal written earlier is
        not skipped. Momentary kinds (aftertouch) are not
        state and are excluded. O(total controls); jumps are
        rare (rehearsal), so no per-step precomputation.
        """

        state = {}

        def absorb(event):
            if event.kind == "control":
                key = ("control", event.channel, event.data1)
            elif event.kind in ("program", "pitchwheel"):
                key = (event.kind, event.channel)
            else:
                return
            state[key] = event

        for event in self.setup:
            absorb(event)

        for step in self.steps[:step_index]:
            for event in step.controls:
                absorb(event)

        return sorted(
            state.values(), key=lambda e: (e.tick, e.channel)
        )
