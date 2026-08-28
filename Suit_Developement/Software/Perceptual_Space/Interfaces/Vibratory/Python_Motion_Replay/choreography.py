"""Loads a recorded choreography CSV and cuts it into movements.

The CSV is the one produced by the previous project
(Python_Motion_Recorder). Its layout, quoted from its README:

  * one row per record, column "record_type" is "sample" or "marker";
  * markers carry event = START / END, a movement_id and the
    sample_index the movement starts at (or ends before);
  * a movement is made of the samples such that
        START.sample_index <= sample_index < END.sample_index ;
  * each IMU owns 32 columns prefixed with its body name, among them
    <name>_ok and <name>_qw/_qx/_qy/_qz.

Nothing here invents data: a sample whose quaternion is missing, not
numeric or not unit is simply not used, and an IMU that has no usable
sample at the end of a movement gets no target for that movement.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import numpy as np

import config
import orientation

#: The eight sensors, in the order the firmware sends them
#: (BODY_NAMES in Arduino_Suit_ESP32_Get_Data_V4/json.cpp).
IMU_NAMES = [
    "back_upper",
    "back_lower",
    "left_arm",
    "right_arm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
]

#: Columns every recording must have for this program to work.
REQUIRED_COLUMNS = [
    "record_type",
    "sample_index",
    "event",
    "movement_id",
    "pc_time_unix",
]


class ChoreographyError(Exception):
    """The CSV cannot be used as a choreography (with the reason)."""


# ----------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------


@dataclass
class Sample:
    """One recorded MQTT message, reduced to what this project needs."""

    index: int
    time_s: float
    quaternions: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class Target:
    """The final orientation of one IMU at the end of one movement."""

    quaternion: np.ndarray
    dispersion_deg: float
    samples_used: int

    @property
    def is_stable(self) -> bool:
        return self.dispersion_deg <= config.REFERENCE_MAX_DISPERSION_DEG


@dataclass
class Movement:
    """One segment of the choreography, between a START and an END."""

    number: int
    start_index: int
    end_index: int
    samples: list[Sample]
    targets: dict[str, Target]

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def duration_s(self) -> float:
        if len(self.samples) < 2:
            return 0.0

        return self.samples[-1].time_s - self.samples[0].time_s

    def trajectory(self, imu_name: str) -> list[np.ndarray]:
        """Every valid orientation of one IMU during the movement."""
        return [
            sample.quaternions[imu_name]
            for sample in self.samples
            if imu_name in sample.quaternions
        ]


@dataclass
class Choreography:
    """A whole recording: its movements and the pose it started from."""

    path: str
    movements: list[Movement]
    neutral: dict[str, np.ndarray]
    warnings: list[str]
    sample_rate_hz: float
    sample_count: int

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def imu_names(self) -> list[str]:
        """IMUs that have a target in every movement.

        Only those can be compared for the whole choreography.
        """
        return [
            name
            for name in IMU_NAMES
            if all(name in movement.targets for movement in self.movements)
        ]


# ----------------------------------------------------------------------
# Reading the file
# ----------------------------------------------------------------------


def _read_quaternion(row: dict, imu_name: str) -> np.ndarray | None:
    """Return the quaternion of one IMU in one row, or None.

    None means "this sensor said nothing usable here": the read failed
    (ok = 0), a cell is empty, or the four numbers are not a rotation.
    """
    if row.get(imu_name + "_ok", "").strip() not in ("1", "1.0", "true", "True"):
        return None

    values = []

    for suffix in ("_qw", "_qx", "_qy", "_qz"):
        text = row.get(imu_name + suffix, "")

        if text is None or text.strip() == "":
            return None

        try:
            values.append(float(text))
        except ValueError:
            return None

    if not orientation.is_valid(values):
        return None

    return orientation.canonical(orientation.normalize(values))


def _read_rows(path: str) -> tuple[list[Sample], list[dict], list[str]]:
    """Split the file into samples and markers."""
    warnings: list[str] = []

    try:
        handle = open(path, newline="", encoding="utf-8")
    except OSError as error:
        raise ChoreographyError("cannot open %s: %s" % (path, error))

    with handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ChoreographyError("%s is empty" % os.path.basename(path))

        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise ChoreographyError(
                "%s is not a motion recording: missing column(s) %s"
                % (os.path.basename(path), ", ".join(missing))
            )

        known_imus = [
            name
            for name in IMU_NAMES
            if name + "_qw" in reader.fieldnames
        ]

        if not known_imus:
            raise ChoreographyError(
                "%s has no IMU column (expected for example left_arm_qw)"
                % os.path.basename(path)
            )

        samples: list[Sample] = []
        markers: list[dict] = []
        bad_rows = 0

        for row in reader:
            record_type = (row.get("record_type") or "").strip()

            try:
                index = int(float(row.get("sample_index") or ""))
            except ValueError:
                bad_rows += 1
                continue

            if record_type == "marker":
                markers.append({
                    "event": (row.get("event") or "").strip().upper(),
                    "sample_index": index,
                    "movement_id": (row.get("movement_id") or "").strip(),
                })
                continue

            if record_type != "sample":
                bad_rows += 1
                continue

            try:
                time_s = float(row.get("pc_time_unix") or "")
            except ValueError:
                bad_rows += 1
                continue

            quaternions = {}

            for imu_name in known_imus:
                quaternion = _read_quaternion(row, imu_name)

                if quaternion is not None:
                    quaternions[imu_name] = quaternion

            samples.append(Sample(index, time_s, quaternions))

    if bad_rows:
        warnings.append("%d unreadable row(s) skipped" % bad_rows)

    return samples, markers, warnings


def _pair_markers(markers: list[dict], warnings: list[str]) -> list[tuple[int, int, int]]:
    """Turn the marker list into (movement number, start, end) triplets."""
    pairs: list[tuple[int, int, int]] = []
    pending: dict | None = None

    for marker in markers:
        event = marker["event"]

        if event == "START":
            if pending is not None:
                warnings.append(
                    "movement starting at sample %d has no END marker, skipped"
                    % pending["sample_index"]
                )

            pending = marker
            continue

        if event == "END":
            if pending is None:
                warnings.append(
                    "END marker at sample %d has no START, skipped"
                    % marker["sample_index"]
                )
                continue

            pairs.append((
                len(pairs) + 1,
                pending["sample_index"],
                marker["sample_index"],
            ))

            pending = None
            continue

        warnings.append("unknown marker event %r skipped" % event)

    if pending is not None:
        warnings.append(
            "the recording ends inside movement %s (no END marker), skipped"
            % (pending["movement_id"] or "?")
        )

    return pairs


# ----------------------------------------------------------------------
# Reference poses
# ----------------------------------------------------------------------


def _final_window(samples: list[Sample]) -> list[Sample]:
    """The samples of the stable pose at the end of a movement.

    Everything from the last REFERENCE_WINDOW_S seconds; if the
    movement is shorter than that (or its timestamps are unusable), the
    last REFERENCE_MIN_SAMPLES samples.
    """
    if not samples:
        return []

    end_time = samples[-1].time_s

    window = [
        sample
        for sample in samples
        if end_time - sample.time_s <= config.REFERENCE_WINDOW_S
    ]

    if len(window) < config.REFERENCE_MIN_SAMPLES:
        window = samples[-config.REFERENCE_MIN_SAMPLES:]

    return window


def _targets_from(window: list[Sample]) -> dict[str, Target]:
    """Average orientation of every IMU over the final window."""
    targets: dict[str, Target] = {}

    for imu_name in IMU_NAMES:
        quaternions = [
            sample.quaternions[imu_name]
            for sample in window
            if imu_name in sample.quaternions
        ]

        if not quaternions:
            continue        # this sensor said nothing usable: no target

        mean = orientation.average(quaternions)

        if mean is None:
            continue

        targets[imu_name] = Target(
            quaternion=mean,
            dispersion_deg=orientation.dispersion_deg(quaternions, mean),
            samples_used=len(quaternions),
        )

    return targets


def _neutral_pose(
    samples: list[Sample], first_start: int | None
) -> dict[str, np.ndarray]:
    """Average pose before the choreography starts.

    Used only by the optional neutral alignment: it is the posture the
    performer stood in before the first movement, which the live user
    can reproduce to cancel a different T-pose calibration.
    """
    if not samples:
        return {}

    if first_start is None:
        candidates = samples
    else:
        candidates = [
            sample for sample in samples if sample.index < first_start
        ]

    if not candidates:
        candidates = samples[: max(1, config.REFERENCE_MIN_SAMPLES)]

    end_time = candidates[-1].time_s

    window = [
        sample
        for sample in candidates
        if end_time - sample.time_s <= config.NEUTRAL_WINDOW_S
    ] or candidates[-config.REFERENCE_MIN_SAMPLES:]

    neutral: dict[str, np.ndarray] = {}

    for imu_name in IMU_NAMES:
        quaternions = [
            sample.quaternions[imu_name]
            for sample in window
            if imu_name in sample.quaternions
        ]

        mean = orientation.average(quaternions) if quaternions else None

        if mean is not None:
            neutral[imu_name] = mean

    return neutral


def _sample_rate(samples: list[Sample]) -> float:
    """Median rate of the recording, in Hz."""
    if len(samples) < 3:
        return 0.0

    deltas = [
        samples[i + 1].time_s - samples[i].time_s
        for i in range(len(samples) - 1)
    ]

    deltas = [delta for delta in deltas if delta > 0.0]

    if not deltas:
        return 0.0

    return 1.0 / float(np.median(deltas))


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def load(path: str) -> Choreography:
    """Read a recording and return its movements.

    Raises ChoreographyError with a readable explanation when the file
    cannot be used.
    """
    samples, markers, warnings = _read_rows(path)

    if not samples:
        raise ChoreographyError(
            "%s contains no sample row" % os.path.basename(path)
        )

    if not markers:
        raise ChoreographyError(
            "%s contains no START/END marker: it was recorded without "
            "marking any movement" % os.path.basename(path)
        )

    by_index: dict[int, Sample] = {}

    for sample in samples:
        by_index.setdefault(sample.index, sample)

    pairs = _pair_markers(markers, warnings)

    if not pairs:
        raise ChoreographyError(
            "%s has no complete movement (no START followed by an END)"
            % os.path.basename(path)
        )

    movements: list[Movement] = []

    for number, start, end in pairs:
        segment = [
            sample
            for sample in samples
            if start <= sample.index < end
        ]

        if not segment:
            warnings.append(
                "movement %d covers no sample (START %d, END %d), skipped"
                % (number, start, end)
            )
            continue

        targets = _targets_from(_final_window(segment))

        if not targets:
            warnings.append(
                "movement %d has no usable IMU at its end, skipped" % number
            )
            continue

        movements.append(
            Movement(
                number=len(movements) + 1,
                start_index=start,
                end_index=end,
                samples=segment,
                targets=targets,
            )
        )

    if not movements:
        raise ChoreographyError(
            "%s has no usable movement: every segment is empty or has no "
            "valid quaternion at its end" % os.path.basename(path)
        )

    for movement in movements:
        unstable = [
            name
            for name, target in movement.targets.items()
            if not target.is_stable
        ]

        if unstable:
            warnings.append(
                "movement %d: the body was still moving at the END marker "
                "for %s (target averaged anyway)"
                % (movement.number, ", ".join(sorted(unstable)))
            )

    choreography = Choreography(
        path=path,
        movements=movements,
        neutral=_neutral_pose(samples, pairs[0][1]),
        warnings=warnings,
        sample_rate_hz=_sample_rate(samples),
        sample_count=len(samples),
    )

    if not choreography.imu_names:
        warnings.append(
            "no IMU has a target in every movement: the comparison will "
            "use the IMUs available in each movement"
        )

    return choreography


def list_recordings(directory: str) -> list[str]:
    """Every CSV of a directory, newest first."""
    if not os.path.isdir(directory):
        return []

    paths = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.lower().endswith(".csv")
    ]

    return sorted(paths, key=os.path.getmtime, reverse=True)
