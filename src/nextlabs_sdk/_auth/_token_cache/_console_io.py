from __future__ import annotations

import sys


class ConsoleIO:
    """Console abstraction over the controlling terminal (POSIX ``/dev/tty``)."""

    def isatty(self) -> bool:
        return sys.stdin.isatty()

    def prompt_secret(self, prompt: str) -> str:
        import getpass

        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            return getpass.getpass(prompt, stream=tty)

    def confirm(self, prompt: str) -> bool:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write(prompt)
            tty.flush()
            return tty.readline().strip().lower() in {"y", "yes"}
