"""Non blocking keyboard, so the interface never waits for a key.

Reading a key must never delay the MQTT reception or the guidance loop,
so the keys already pressed are collected and the function returns
immediately when there is none.

Same approach as in the recording project: msvcrt on Windows, a raw
terminal plus select() elsewhere.
"""

from __future__ import annotations

import os
import sys


class KeyReader:
    """Returns the keys typed so far, without ever waiting."""

    def __init__(self) -> None:
        self._windows = os.name == "nt"
        self._fd = None
        self._saved = None

    def __enter__(self) -> "KeyReader":
        if not self._windows:
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._saved = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)

        return self

    def __exit__(self, *exc_info) -> None:
        if not self._windows and self._saved is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)

    def poll(self) -> list[str]:
        if self._windows:
            return self._poll_windows()

        return self._poll_unix()

    def _poll_windows(self) -> list[str]:
        import msvcrt

        keys: list[str] = []

        while msvcrt.kbhit():
            char = msvcrt.getwch()

            # Arrows and function keys arrive as two characters.
            if char in ("\x00", "\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue

            keys.append(char)

        return keys

    def _poll_unix(self) -> list[str]:
        import select

        keys: list[str] = []

        while select.select([sys.stdin], [], [], 0)[0]:
            char = sys.stdin.read(1)

            if not char:
                break

            keys.append(char)

        return strip_escape_sequences(keys)


def strip_escape_sequences(keys: list[str]) -> list[str]:
    """Drop arrow keys and friends, keep a lone ESC (it means quit)."""
    cleaned: list[str] = []
    index = 0

    while index < len(keys):
        char = keys[index]

        if (char == "\x1b"
                and index + 1 < len(keys)
                and keys[index + 1] in ("[", "O")):
            index += 2

            while index < len(keys) and not (
                keys[index].isalpha() or keys[index] == "~"
            ):
                index += 1

            index += 1
            continue

        cleaned.append(char)
        index += 1

    return cleaned
