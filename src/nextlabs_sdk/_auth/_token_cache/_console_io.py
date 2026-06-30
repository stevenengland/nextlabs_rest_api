from __future__ import annotations

import sys


class ConsoleIO:
    """Console abstraction over the controlling terminal (POSIX ``/dev/tty``).

    The terminal is accessed through separate read and write handles rather than
    a single ``"r+"`` handle: the latter is a ``BufferedRandom`` whose flush
    requires seek support, which a non-seekable ``/dev/tty`` (devcontainers, some
    CI shells) does not provide. An unusable terminal therefore surfaces as an
    ``OSError`` (``io.UnsupportedOperation`` included) for callers to treat as
    non-interactive, instead of aborting the command.
    """

    def isatty(self) -> bool:
        return sys.stdin.isatty()

    def prompt_secret(self, prompt: str) -> str:
        import getpass

        with open("/dev/tty", "w", encoding="utf-8") as tty:
            return getpass.getpass(prompt, stream=tty)

    def confirm(self, prompt: str) -> bool:
        with (
            open("/dev/tty", "w", encoding="utf-8") as writer,
            open("/dev/tty", "r", encoding="utf-8") as reader,
        ):
            writer.write(prompt)
            writer.flush()
            return reader.readline().strip().lower() in {"y", "yes"}
