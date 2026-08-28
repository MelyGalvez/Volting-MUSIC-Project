"""The terminal dashboard.

One screen, redrawn UI_REFRESH_HZ times per second, showing everything
the user needs while performing the choreography:

  * which recording is being replayed;
  * which movement, out of how many;
  * the current orientation error and the tolerance it must reach;
  * the progress of the five second hold;
  * which motor is vibrating;
  * the state of the MQTT link.

Rendering is plain text: the screen is cleared and reprinted. No
external library is needed.
"""

from __future__ import annotations

import os
import sys

import config
import guidance

WIDTH = 70


# ----------------------------------------------------------------------
# Terminal helpers
# ----------------------------------------------------------------------


def enable_ansi() -> None:
    """Allow escape sequences on a Windows console (no-op elsewhere)."""
    if os.name != "nt":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()

        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # 0x0004 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def clear() -> None:
    sys.stdout.write("\033[H\033[J")


def bar(fraction: float, width: int, filled: str = "#", empty: str = "-") -> str:
    fraction = max(0.0, min(1.0, fraction))
    count = int(round(fraction * width))

    return filled * count + empty * (width - count)


def _line(char: str = "-") -> str:
    return char * WIDTH


# ----------------------------------------------------------------------
# Screen
# ----------------------------------------------------------------------


def render(choreography, session, evaluation, link, haptic, rate_hz: float) -> str:
    """Build the whole screen as one string."""
    rows: list[str] = []

    rows.append(_line("="))
    rows.append("  MOTION REPLAY  -  guided choreography")
    rows.append(_line("="))

    rows.append("  recording : %-38s" % _shorten(choreography.name, 38))
    rows.append("  movement  : %-38s" % _movement_text(session, evaluation))
    rows.append(
        "  MQTT      : %-16s data %5.1f msg/s   invalid %d"
        % (
            "connected" if link.connected else "OFFLINE",
            rate_hz,
            link.invalid_count,
        )
    )
    rows.append(_line())

    rows.append("  STATE     : %s" % _state_text(evaluation))

    if evaluation.message:
        rows.append("              %s" % evaluation.message)

    rows.append("")
    rows += _error_block(evaluation)
    rows.append("")
    rows += _hold_block(evaluation)
    rows.append("")
    rows += _haptic_block(haptic, evaluation)

    rows.append(_line())
    rows += _per_imu_block(evaluation)

    if session.alignment_active or session.capturing_neutral:
        rows.append(_line())
        rows.append(
            "  neutral alignment : %s"
            % ("CAPTURING..." if session.capturing_neutral
               else "active on %d IMU(s)" % len(session.alignment))
        )

    rows.append(_line())
    rows.append("  [N] capture neutral pose   [S] skip movement   [Q] quit")
    rows.append(_line("="))

    return "\n".join(rows)


def _shorten(text: str, width: int) -> str:
    if len(text) <= width:
        return text

    return "..." + text[-(width - 3):]


def _movement_text(session, evaluation) -> str:
    if evaluation.state == guidance.FINISHED:
        return "all %d movements completed" % session.total

    movement = session.movement

    if movement is None:
        return "-"

    return "%d / %d   (%d recorded samples, %.1f s)" % (
        evaluation.movement_number,
        evaluation.movement_total,
        movement.sample_count,
        movement.duration_s,
    )


def _state_text(evaluation) -> str:
    return {
        guidance.WAITING_DATA: "WAITING FOR DATA",
        guidance.GUIDING: "PERFORM THE MOVEMENT",
        guidance.HOLDING: "ON TARGET - HOLD STILL",
        guidance.FINISHED: "FINISHED",
    }.get(evaluation.state, evaluation.state)


def _error_block(evaluation) -> list[str]:
    if evaluation.error_deg is None:
        return [
            "  ERROR     :   --.- deg      tolerance %.1f deg (exit %.1f)"
            % (config.POSITION_TOLERANCE_DEG, config.EXIT_TOLERANCE_DEG),
            "              %s" % bar(0.0, 46),
        ]

    scale = max(config.HAPTIC_FULL_INTENSITY_DEG, config.EXIT_TOLERANCE_DEG * 2)
    fraction = 1.0 - min(1.0, evaluation.error_deg / scale)

    return [
        "  ERROR     : %6.1f deg      tolerance %.1f deg (exit %.1f)"
        % (
            evaluation.error_deg,
            config.POSITION_TOLERANCE_DEG,
            config.EXIT_TOLERANCE_DEG,
        ),
        "              %s  %s"
        % (bar(fraction, 40), "IN" if evaluation.inside else "out"),
        "              worst sensor: %s" % (evaluation.worst_imu or "-"),
    ]


def _hold_block(evaluation) -> list[str]:
    return [
        "  HOLD      : %4.1f / %.1f s"
        % (evaluation.hold_elapsed_s, config.HOLD_DURATION_S),
        "              %s" % bar(evaluation.hold_progress, 40, "="),
    ]


def _haptic_block(haptic, evaluation) -> list[str]:
    left = "LEFT  [%s]" % ("##" if haptic.left > 0 else "  ")
    right = "RIGHT [%s]" % ("##" if haptic.right > 0 else "  ")

    detail = "silent"

    if haptic.left > 0 or haptic.right > 0:
        detail = "pulse %.1f Hz, %d ms, power %.2f" % (
            haptic.pulse_hz,
            config.HAPTIC_PULSE_MS,
            max(haptic.left, haptic.right),
        )

    rows = ["  VIBRATION : %s   %s    %s" % (left, right, detail)]

    if not config.HAPTICS_ENABLED:
        rows.append("              (haptics disabled in config)")
    elif haptic.last_error:
        rows.append("              command %s" % haptic.last_error)
    else:
        rows.append(
            "              direction: %s   commands sent: %d"
            % (evaluation.direction, haptic.sent_count)
        )

    return rows


def _per_imu_block(evaluation) -> list[str]:
    if not evaluation.per_imu:
        return ["  (no sensor compared yet)"]

    ordered = sorted(
        evaluation.per_imu.values(),
        key=lambda item: item.error_deg,
        reverse=True,
    )

    rows = ["  per sensor (deg, and the turn part of the correction):"]

    for item in ordered[:8]:
        turn = "   --" if item.turn_deg is None else "%+5.1f" % item.turn_deg

        rows.append(
            "     %-14s %6.1f    turn %s   other %5.1f"
            % (item.name, item.error_deg, turn, item.residual_deg)
        )

    return rows


# ----------------------------------------------------------------------
# Static screens
# ----------------------------------------------------------------------


def choreography_summary(choreography) -> str:
    """What was loaded, printed once before the session starts."""
    rows = [
        _line("="),
        "  Loaded: %s" % choreography.name,
        _line("="),
        "  %d movement(s), %d samples, %.1f Hz recording"
        % (
            len(choreography.movements),
            choreography.sample_count,
            choreography.sample_rate_hz,
        ),
        "",
    ]

    for movement in choreography.movements:
        stable = [
            name for name, target in movement.targets.items()
            if target.is_stable
        ]

        rows.append(
            "   movement %-2d  %5.1f s  %4d samples  "
            "target on %d IMU(s), %d stable"
            % (
                movement.number,
                movement.duration_s,
                movement.sample_count,
                len(movement.targets),
                len(stable),
            )
        )

    compared = config.COMPARE_IMUS or tuple(choreography.imu_names)

    rows.append("")
    rows.append(
        "  compared sensors: %s"
        % (", ".join(compared) if compared else "the ones available per movement")
    )
    rows.append(
        "  tolerance %.1f deg (exit %.1f), hold %.1f s, aggregation '%s'"
        % (
            config.POSITION_TOLERANCE_DEG,
            config.EXIT_TOLERANCE_DEG,
            config.HOLD_DURATION_S,
            config.ERROR_AGGREGATION,
        )
    )

    if choreography.warnings:
        rows.append("")
        rows.append("  warnings:")

        for warning in choreography.warnings:
            rows.append("   - %s" % warning)

    rows.append(_line("="))

    return "\n".join(rows)


def session_summary(session) -> str:
    """The report printed when the session ends."""
    rows = ["", _line("="), "  SESSION REPORT", _line("=")]

    if not session.results:
        rows.append("  no movement was completed")
    else:
        for result in session.results:
            if result.skipped:
                rows.append(
                    "   movement %-2d  SKIPPED       after %5.1f s"
                    % (result.number, result.seconds)
                )
                continue

            score = (
                ""
                if result.trajectory_score_deg is None
                else "   path score %5.1f deg" % result.trajectory_score_deg
            )

            rows.append(
                "   movement %-2d  validated in %5.1f s   final error %4.1f deg%s"
                % (
                    result.number,
                    result.seconds,
                    result.final_error_deg,
                    score,
                )
            )

    done = sum(1 for result in session.results if not result.skipped)

    rows.append("")
    rows.append("  %d / %d movement(s) validated" % (done, session.total))
    rows.append(_line("="))

    return "\n".join(rows)
