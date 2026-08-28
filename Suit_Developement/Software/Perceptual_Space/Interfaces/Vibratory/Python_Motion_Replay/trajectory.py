"""Optional quality score: how close the whole path was, not just its end.

The progression criterion of the session is the final position plus the
five second hold. This module adds nothing to that decision: it only
produces, once a movement is validated, one number that summarises how
similar the performed trajectory was to the recorded one.

Method: dynamic time warping (DTW) with the quaternion geodesic angle
as the local cost. DTW is the standard way to compare two gestures
performed at different speeds - it looks for the alignment between the
two time series that minimises the accumulated distance, so a user who
is slower than the recording is not penalised for the delay, only for
the shape of the movement.

The returned score is the average angular distance along that optimal
alignment, in degrees: 0 would be a perfect copy, 20 means the paths
differ by about twenty degrees on average.
"""

from __future__ import annotations

import numpy as np

import config
from choreography import Movement

#: Below this many frames a trajectory is too short to compare.
_MIN_FRAMES = 4


def _resample(sequence: list, count: int) -> list:
    """Pick at most `count` frames, evenly spread over the sequence."""
    if len(sequence) <= count:
        return sequence

    positions = np.linspace(0, len(sequence) - 1, count)

    return [sequence[int(round(position))] for position in positions]


def _cost_matrix(reference: list[dict], live: list[dict], names: list[str]) -> np.ndarray:
    """Mean geodesic angle, in degrees, between every pair of frames.

    Computed with matrix products rather than one pair at a time: the
    angle between two unit quaternions is 2*acos(|dot|), and all the
    dot products of two sequences are a single matrix multiplication.
    """
    total = np.zeros((len(reference), len(live)))

    for name in names:
        left = np.array([frame[name] for frame in reference])
        right = np.array([frame[name] for frame in live])

        dots = np.clip(np.abs(left @ right.T), 0.0, 1.0)

        total += np.degrees(2.0 * np.arccos(dots))

    return total / len(names)


def _dtw(cost: np.ndarray) -> float:
    """Average cost along the cheapest monotonic alignment."""
    rows, columns = cost.shape

    # accumulated[i][j] = best total cost to reach (i, j)
    accumulated = np.full((rows + 1, columns + 1), np.inf)
    steps = np.zeros((rows + 1, columns + 1))
    accumulated[0, 0] = 0.0

    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            previous = (
                (accumulated[i - 1, j - 1], steps[i - 1, j - 1]),
                (accumulated[i - 1, j], steps[i - 1, j]),
                (accumulated[i, j - 1], steps[i, j - 1]),
            )

            best_cost, best_steps = min(previous, key=lambda item: item[0])

            accumulated[i, j] = cost[i - 1, j - 1] + best_cost
            steps[i, j] = best_steps + 1

    path_length = steps[rows, columns]

    if path_length <= 0:
        return float("nan")

    return float(accumulated[rows, columns] / path_length)


def score(movement: Movement, live_trajectory: list[dict]) -> float | None:
    """Average angular distance between the performed and recorded paths.

    Returns None when there is not enough common data to compare, which
    is not a failure: the session simply shows no score.
    """
    if not live_trajectory or len(live_trajectory) < _MIN_FRAMES:
        return None

    # Only the sensors present in the target, in the recorded samples
    # and in every live frame can be compared.
    names = [
        name
        for name in movement.targets
        if all(name in frame for frame in live_trajectory)
    ]

    reference_frames = [
        {name: sample.quaternions[name] for name in names}
        for sample in movement.samples
        if all(name in sample.quaternions for name in names)
    ]

    if not names or len(reference_frames) < _MIN_FRAMES:
        return None

    reference = _resample(reference_frames, config.DTW_MAX_POINTS)
    live = _resample(live_trajectory, config.DTW_MAX_POINTS)

    try:
        return _dtw(_cost_matrix(reference, live, names))
    except (ValueError, KeyError):
        return None
