# =================================================
# RELEASE MODES
#
# Strategies deciding *when notes end* once a step
# has been fired. The navigation engine always
# applies the deterministic positional rule (a note
# is released when the musical position passes its
# written end tick); a release mode may additionally
# request time-scheduled releases.
#
# The interface is deliberately small so future
# playback modes (beat-conducting, gate/held-gesture
# modes, ...) are new classes, not engine changes:
#
#   name                  short identifier for UI/config
#   reset()               forget pace/history (load, jump,
#                         silence)
#   on_step(step, now)    called after a step's notes were
#                         started; returns an iterable of
#                         ((channel, key), due_monotonic)
#                         release requests
# =================================================


class SustainRelease:
    """
    Notes sound until the musical position passes their
    written end (evaluated at each gesture) — the engine's
    built-in rule, so this mode schedules nothing. Fully
    deterministic: the same gesture sequence always yields
    the same MIDI output, independent of wall-clock time.
    """

    name = "sustain"

    def reset(self):
        pass

    def on_step(self, step, now):
        return ()


class TimedRelease:
    """
    Note durations follow the file, scaled by the
    performer's current pace, so articulation (staccato,
    tenuto) survives even between slow gestures.

    Pace = file-seconds per wall-second, estimated from
    the gaps between consecutive fired steps with an
    exponential moving average. Instantaneous estimates
    and resulting durations are clamped so a hesitation
    or a double hit cannot produce absurd note lengths.

    The engine's positional rule still applies on top:
    whichever comes first — the scheduled release or the
    musical position passing the note's end — ends the
    note, so no note ever outlives its written context.
    """

    name = "timed"

    def __init__(
        self,
        *,
        alpha=0.4,
        rate_min=0.2,
        rate_max=5.0,
        min_gate_s=0.05,
        max_hold_s=10.0,
    ):
        self._alpha = alpha
        self._rate_min = rate_min
        self._rate_max = rate_max
        self._min_gate = min_gate_s
        self._max_hold = max_hold_s

        self.rate = 1.0
        self._last_file_s = None
        self._last_mono = None

    def reset(self):
        self.rate = 1.0
        self._last_file_s = None
        self._last_mono = None

    def on_step(self, step, now):
        if self._last_mono is not None:
            file_gap = step.time_s - self._last_file_s
            wall_gap = now - self._last_mono

            if file_gap > 0.0 and wall_gap > 1e-3:
                instant = file_gap / wall_gap
                instant = max(
                    self._rate_min, min(self._rate_max, instant)
                )
                self.rate += self._alpha * (instant - self.rate)

        self._last_file_s = step.time_s
        self._last_mono = now

        requests = []
        for note in step.notes:
            duration = note.duration_s / self.rate
            duration = max(
                self._min_gate, min(self._max_hold, duration)
            )
            requests.append(
                ((note.channel, note.key), now + duration)
            )

        return requests


def make_release_mode(name, cfg):
    """
    Build the release mode selected by name, parameterized
    from the config module. Unknown names fail at startup.
    """

    if name == "sustain":
        return SustainRelease()

    if name == "timed":
        return TimedRelease(
            alpha=cfg.TIMED_RATE_ALPHA,
            rate_min=cfg.TIMED_RATE_MIN,
            rate_max=cfg.TIMED_RATE_MAX,
            min_gate_s=cfg.TIMED_MIN_GATE_S,
            max_hold_s=cfg.TIMED_MAX_HOLD_S,
        )

    raise ValueError(f"Unknown release mode: {name!r}")
