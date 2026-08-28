"""The rule of the session: compare, hold five seconds, move on.

For the current movement the program knows one target orientation per
IMU, taken from the end of the recorded movement. Every time a live
sample arrives it computes, for each compared sensor, the angle that
still separates the user from that target:

    q_error = conj(q_live) * q_target        (both T-pose relative)
    error   = 2 * atan2(|vector part|, |w|)

That angle is the geodesic distance on the rotation group: the single
rotation that would bring the user exactly onto the reference. It does
not care which Euler convention was used, and it has no gimbal lock and
no 0/360 jump.

The movement is validated when the aggregated error stays under the
tolerance for HOLD_DURATION_S seconds without interruption. Hysteresis
(a wider exit tolerance) keeps a small tremor around the boundary from
restarting the timer several times per second.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

import config
import orientation
import trajectory as trajectory_module
from choreography import Choreography, Movement
from live_data import LiveState

#: Session states, shown as such in the interface.
WAITING_DATA = "waiting_data"
GUIDING = "guiding"
HOLDING = "holding"
FINISHED = "finished"

#: Haptic directions.
LEFT = "left"
RIGHT = "right"
BOTH = "both"
NONE = "none"


@dataclass
class ImuError:
    """How far one sensor is from its target, and in which sense."""

    name: str
    error_deg: float

    #: Part of the correction that is a turn around the vertical axis,
    #: in degrees. Positive = the user must turn to their left. None
    #: when the gravity vector was unusable.
    turn_deg: float | None

    #: Part of the correction that is NOT a turn (bending, lifting).
    residual_deg: float


@dataclass
class MovementResult:
    """What happened on one movement."""

    number: int
    final_error_deg: float
    seconds: float
    skipped: bool = False
    trajectory_score_deg: float | None = None


@dataclass
class Evaluation:
    """Everything the interface and the haptics need, for one instant."""

    state: str
    movement_number: int
    movement_total: int
    error_deg: float | None = None
    per_imu: dict[str, ImuError] = field(default_factory=dict)
    worst_imu: str | None = None
    inside: bool = False
    hold_elapsed_s: float = 0.0
    direction: str = NONE
    message: str = ""

    @property
    def hold_progress(self) -> float:
        if config.HOLD_DURATION_S <= 0.0:
            return 1.0

        return max(0.0, min(1.0, self.hold_elapsed_s / config.HOLD_DURATION_S))


class GuidanceSession:
    """Walks the user through the choreography, one movement at a time."""

    def __init__(self, choreography: Choreography) -> None:
        self.choreography = choreography
        self.index = 0
        self.results: list[MovementResult] = []

        #: Per IMU alignment applied to the live orientation (identity
        #: unless a neutral pose has been captured).
        self.alignment: dict[str, np.ndarray] = {}
        self.alignment_active = False

        self._hold_start: float | None = None
        self._movement_start: float = time.monotonic()

        #: Live trajectory of the current movement, for the optional
        #: trajectory score.
        self._live_trajectory: list[dict[str, np.ndarray]] = []

        #: Neutral capture in progress.
        self._capture_until: float | None = None
        self._capture: dict[str, list[np.ndarray]] = {}

    # -- current movement ---------------------------------------------

    @property
    def movement(self) -> Movement | None:
        if self.index >= len(self.choreography.movements):
            return None

        return self.choreography.movements[self.index]

    @property
    def total(self) -> int:
        return len(self.choreography.movements)

    @property
    def finished(self) -> bool:
        return self.index >= self.total

    # -- neutral alignment --------------------------------------------

    def start_neutral_capture(self, now: float | None = None) -> None:
        """Begin recording the live neutral pose (N key)."""
        moment = time.monotonic() if now is None else now

        self._capture_until = moment + config.NEUTRAL_CAPTURE_S
        self._capture = {}

    @property
    def capturing_neutral(self) -> bool:
        return self._capture_until is not None

    def _run_capture(self, live: dict, now: float) -> None:
        """Collect samples, then build the alignment quaternions."""
        for name, imu in live.items():
            self._capture.setdefault(name, []).append(imu.quaternion)

        if now < (self._capture_until or 0.0):
            return

        self._capture_until = None

        alignment: dict[str, np.ndarray] = {}

        for name, quaternions in self._capture.items():
            reference = self.choreography.neutral.get(name)
            measured = orientation.average(quaternions)

            if reference is None or measured is None:
                continue

            # Both poses describe the same physical posture, so the
            # rotation between the two calibration frames is
            #     A = q_reference_neutral * conj(q_live_neutral)
            # and the live orientation is compared as A * q_live.
            alignment[name] = orientation.canonical(
                orientation.multiply(
                    reference, orientation.conjugate(measured)
                )
            )

        self._capture = {}

        if alignment:
            self.alignment = alignment
            self.alignment_active = True

    def clear_alignment(self) -> None:
        self.alignment = {}
        self.alignment_active = False

    def _aligned(self, name: str, quaternion: np.ndarray) -> np.ndarray:
        matrix = self.alignment.get(name)

        if matrix is None:
            return quaternion

        return orientation.multiply(matrix, quaternion)

    # -- main evaluation ----------------------------------------------

    def evaluate(self, state: LiveState | None, now: float | None = None) -> Evaluation:
        """Compare the live pose with the current target, advance if held."""
        moment = time.monotonic() if now is None else now

        if self.finished:
            return Evaluation(FINISHED, self.total, self.total,
                              message="choreography complete")

        movement = self.movement
        assert movement is not None

        live = state.fresh_imus(moment) if state is not None else {}

        if self.capturing_neutral and live:
            self._run_capture(live, moment)

        if not live:
            self._reset_hold()

            return Evaluation(
                WAITING_DATA, movement.number, self.total,
                message="no live data from the suit",
            )

        per_imu = self._compare(movement, live)

        if not per_imu:
            self._reset_hold()

            return Evaluation(
                WAITING_DATA, movement.number, self.total,
                message="no IMU is present in both the recording and the "
                        "live data",
            )

        error = _aggregate(
            [item.error_deg for item in per_imu.values()]
        )

        worst = max(per_imu.values(), key=lambda item: item.error_deg)

        self._buffer_trajectory(live)

        inside = self._update_hold(error, moment)

        if inside and self._elapsed(moment) >= config.HOLD_DURATION_S:
            self._complete(movement, error, moment)

            if self.finished:
                return Evaluation(FINISHED, self.total, self.total,
                                  message="choreography complete")

            return Evaluation(
                GUIDING, self.movement.number, self.total,
                error_deg=error, per_imu=per_imu, worst_imu=worst.name,
                message="movement %d validated" % movement.number,
            )

        return Evaluation(
            HOLDING if inside else GUIDING,
            movement.number,
            self.total,
            error_deg=error,
            per_imu=per_imu,
            worst_imu=worst.name,
            inside=inside,
            hold_elapsed_s=self._elapsed(moment) if inside else 0.0,
            direction=NONE if inside else _direction(worst),
            message="hold the position" if inside else "",
        )

    # -- comparison ----------------------------------------------------

    def _compare(self, movement: Movement, live: dict) -> dict[str, ImuError]:
        """One ImuError per sensor present in both the target and live."""
        wanted = config.COMPARE_IMUS or tuple(movement.targets)

        errors: dict[str, ImuError] = {}

        for name in wanted:
            target = movement.targets.get(name)
            measured = live.get(name)

            if target is None or measured is None:
                continue

            current = self._aligned(name, measured.quaternion)

            error_quaternion = orientation.error_rotation(
                current, target.quaternion
            )

            error_deg = orientation.angle_deg(error_quaternion)

            turn_deg, residual_deg = _split_correction(
                orientation.rotation_vector_deg(error_quaternion),
                measured.gravity,
            )

            errors[name] = ImuError(name, error_deg, turn_deg, residual_deg)

        return errors

    # -- hold timer ----------------------------------------------------

    def _update_hold(self, error: float, now: float) -> bool:
        """Apply the tolerance with hysteresis, return True while inside."""
        if self._hold_start is None:
            if error <= config.POSITION_TOLERANCE_DEG:
                self._hold_start = now
                return True

            return False

        # Already holding: a wider tolerance keeps the timer running
        # through small oscillations.
        if error <= config.EXIT_TOLERANCE_DEG:
            return True

        self._hold_start = None

        return False

    def _elapsed(self, now: float) -> float:
        if self._hold_start is None:
            return 0.0

        return now - self._hold_start

    def _reset_hold(self) -> None:
        self._hold_start = None

    # -- progression ---------------------------------------------------

    def _buffer_trajectory(self, live: dict) -> None:
        if not config.ENABLE_TRAJECTORY_SCORE:
            return

        # A bounded buffer: a very long movement cannot exhaust memory.
        if len(self._live_trajectory) >= 20000:
            return

        self._live_trajectory.append({
            name: self._aligned(name, imu.quaternion)
            for name, imu in live.items()
        })

    def _complete(self, movement: Movement, error: float, now: float) -> None:
        score = None

        if config.ENABLE_TRAJECTORY_SCORE:
            score = trajectory_module.score(movement, self._live_trajectory)

        self.results.append(
            MovementResult(
                number=movement.number,
                final_error_deg=error,
                seconds=now - self._movement_start,
                trajectory_score_deg=score,
            )
        )

        self._advance(now)

    def skip(self, now: float | None = None) -> None:
        """Give up on the current movement and go to the next one."""
        moment = time.monotonic() if now is None else now

        movement = self.movement

        if movement is None:
            return

        self.results.append(
            MovementResult(
                number=movement.number,
                final_error_deg=float("nan"),
                seconds=moment - self._movement_start,
                skipped=True,
            )
        )

        self._advance(moment)

    def _advance(self, now: float) -> None:
        self.index += 1
        self._hold_start = None
        self._movement_start = now
        self._live_trajectory = []


# ----------------------------------------------------------------------
# Free functions
# ----------------------------------------------------------------------


def _aggregate(errors: list[float]) -> float:
    """Turn the per-IMU errors into the number that drives the session."""
    if not errors:
        return float("nan")

    if config.ERROR_AGGREGATION == "mean":
        return float(np.mean(errors))

    # Default: the worst body segment decides, so no sensor can be far
    # from the target while the movement is validated.
    return float(max(errors))


def _split_correction(rotation_vector: np.ndarray, gravity) -> tuple[float | None, float]:
    """Split the correction into "turn" and "everything else".

    The rotation vector is the rotation the user must still perform,
    with its axis expressed in the sensor frame. The gravity vector the
    same sensor reports is expressed in that same frame and points up
    (the BNO055 follows the accelerometer sign convention: flat sensor,
    Z up, reads +9.81 on Z, and ACC = LIA + GRV).

    Projecting one onto the other therefore separates:

      * the component around the vertical axis, which is a turn to the
        left (positive, right hand rule around "up") or to the right;
      * the rest, which is a bend or a lift and has no left/right
        meaning.

    Nothing here depends on a Euler convention or on how the sensor is
    mounted on the body.
    """
    total = float(np.linalg.norm(rotation_vector))

    up = orientation.unit_vector(gravity)

    if up is None:
        return None, total

    magnitude = float(np.linalg.norm(np.asarray(gravity, dtype=float)))

    if not (config.GRAVITY_MIN_MAGNITUDE
            <= magnitude
            <= config.GRAVITY_MAX_MAGNITUDE):
        # Not a sensor at rest in the earth field: the direction cannot
        # be trusted, so no side is claimed.
        return None, total

    if not config.GRAVITY_VECTOR_POINTS_UP:
        up = -up

    turn = float(np.dot(rotation_vector, up))

    residual = float(np.linalg.norm(rotation_vector - turn * up))

    return turn, residual


def _direction(worst: ImuError) -> str:
    """Which motor should pulse for the sensor that is furthest off."""
    if worst.turn_deg is None:
        return BOTH

    if abs(worst.turn_deg) < config.DIRECTION_DEADBAND_DEG:
        return BOTH

    total = max(worst.error_deg, 1e-6)

    if abs(worst.turn_deg) < config.DIRECTION_DOMINANCE * total:
        # The correction is mostly out of the horizontal plane: telling
        # the user "left" would be misleading.
        return BOTH

    return LEFT if worst.turn_deg > 0.0 else RIGHT
