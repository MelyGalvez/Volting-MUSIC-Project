# =================================================
# GESTURE ROUTER
#
# Owns the configured detectors and translates their
# events into navigation actions ("advance"/"back")
# according to config.GESTURE_MAP. Gates everything
# on the suit's system state: pose data is only
# meaningful in "ready" and "degraded" (PROTOCOL.md),
# and a performer holding the calibration T-pose must
# never advance the score.
#
# Pure translation — the router performs no I/O and
# dispatches nothing; the composition root decides
# what to do with the returned actions. That keeps
# this module trivially unit-testable and lets future
# input sources (live MIDI input, foot pedals) join
# by adding detectors with new source names.
# =================================================

RUNNING_STATES = ("ready", "degraded")

ACTIONS = ("advance", "back")


class GestureRouter:

    def __init__(self, detectors, gesture_map):
        """
        detectors: iterable of objects with .source,
        .process(packet, mono) -> [GestureEvent], .reset().
        gesture_map: source name -> action name ("off"
        disables a source without removing its config).
        """

        self._detectors = []

        for detector in detectors:
            action = gesture_map.get(detector.source, "off")

            if action == "off":
                continue
            if action not in ACTIONS:
                raise ValueError(
                    f"Unknown action {action!r} for gesture "
                    f"source {detector.source!r}"
                )

            self._detectors.append((detector, action))

    def process(self, packet, mono):
        """
        Run every active detector on one fresh frame.
        Returns [(action, GestureEvent), ...] in detector
        order (piezo before swings as configured, so the
        lowest-latency source wins the refractory race).
        """

        if packet.get("system") not in RUNNING_STATES:
            # Calibration / boot / error: drop detector
            # state so nothing fires on the transition
            # back to running.
            self.reset()
            return []

        actions = []

        for detector, action in self._detectors:
            for event in detector.process(packet, mono):
                actions.append((action, event))

        return actions

    def reset(self):
        for detector, _action in self._detectors:
            detector.reset()

    @property
    def active_sources(self):
        return tuple(d.source for d, _a in self._detectors)
