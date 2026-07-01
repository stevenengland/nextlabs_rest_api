from __future__ import annotations

import sys

_TTY_PATH = "/dev/tty"
_ENCODING = "utf-8"


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

        with open(_TTY_PATH, "w", encoding=_ENCODING) as tty:
            return getpass.getpass(prompt, stream=tty)

    def message(self, text: str) -> None:
        """Write one line to the controlling terminal, ignoring an unusable one.

        Unlike stderr diagnostics, hints go to ``/dev/tty`` so they appear next
        to the prompt and survive stdout/stderr redirection. A terminal that
        cannot be opened is treated as non-interactive: the hint is dropped
        rather than raising, mirroring the other prompt handles.
        """
        try:
            with open(_TTY_PATH, "w", encoding=_ENCODING) as writer:
                writer.write(f"{text}\n")
                writer.flush()
        except OSError:
            return

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        with (
            open(_TTY_PATH, "w", encoding=_ENCODING) as writer,
            open(_TTY_PATH, "r", encoding=_ENCODING) as reader,
        ):
            writer.write(prompt)
            writer.flush()
            answer = reader.readline().strip().lower()
        if not answer:
            return default
        return answer in {"y", "yes"}
