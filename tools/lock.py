"""Regenerate ``requirements/constraints.txt`` via pip-compile.

Default mode overwrites the committed lock in place. ``--check`` compiles
to a scratch location and exits non-zero if the result differs from the
committed lock, without writing anything.

Inputs: ``pyproject.toml`` (direct runtime dependencies and every optional
extra), the committed ``requirements/dev-compile.in`` (unpinned dev tool
names) and ``requirements/overrides.in`` (deliberate transitive pins). The
full transitive closure is pinned with ``==``, extras stripped, no hashes.

The script refuses to run under a Python minor version other than the
devcontainer image's, since the resolved closure is Python-version
specific.

A non-zero exit from the compiler is an expected, actionable outcome —
the source inputs contradict each other — so it is reported as a short
repair instruction next to the compiler's own diagnostic rather than a
traceback. Defects in this script keep raising normally.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / ".devcontainer" / "Dockerfile"
REQUIREMENTS_DIR = ROOT / "requirements"
CONSTRAINTS = REQUIREMENTS_DIR / "constraints.txt"
DEV_COMPILE_INPUT = REQUIREMENTS_DIR / "dev-compile.in"
OVERRIDES = REQUIREMENTS_DIR / "overrides.in"

COMPILER_FAILURE_HINT = (
    "the compiler could not resolve requirements/constraints.txt from its "
    "source inputs (pyproject.toml, requirements/dev-compile.in, "
    "requirements/overrides.in); see the compiler output above, relax or "
    "correct the contradicting source requirement, then regenerate the lock "
    "with `python tools/lock.py`"
)


def _devcontainer_python_minor() -> str:
    """Read the Python minor version pinned by the devcontainer image."""
    match = re.search(r"FROM\s+\S*python:(\d+\.\d+)", DOCKERFILE.read_text())
    if not match:
        sys.exit(f"could not find a 'FROM ...python:X.Y' line in {DOCKERFILE}")
    return match.group(1)


def _guard_python_minor() -> None:
    running = f"{sys.version_info.major}.{sys.version_info.minor}"
    required = _devcontainer_python_minor()
    if running != required:
        sys.exit(
            f"tools/lock.py must run under Python {required} "
            f"(the devcontainer image's minor version), got {running}"
        )


class CompilerFailedError(Exception):
    """The lock compiler rejected the source inputs it was given.

    Signals an expected, actionable compiled-lock problem — a
    contradiction between the source inputs — as opposed to a defect in
    this script, which must keep surfacing its own traceback.
    """

    def __init__(self, returncode: int, diagnostic: str) -> None:
        super().__init__(f"pip-compile exited with {returncode}")
        self.returncode = returncode
        self.diagnostic = diagnostic


def _without_traceback_frames(output: str) -> str:
    """Strip Python traceback frames, keeping the messages around them.

    An expected compiler failure surfaces as a ``pip`` traceback whose
    frames say nothing about the contradicting requirement. The final
    exception line and the compiler's own messages do, so only the
    indented frame block is dropped.
    """
    kept: list[str] = []
    in_frames = False
    for line in output.splitlines():
        if line.startswith("Traceback (most recent call last):"):
            in_frames = True
        elif not (in_frames and line.startswith((" ", "\t"))):
            in_frames = False
            kept.append(line)
    return "\n".join(kept)


def _compile(output_file: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "piptools",
            "compile",
            "--quiet",
            "--strip-extras",
            "--all-extras",
            f"--output-file={output_file}",
            str(Path("pyproject.toml")),
            str(DEV_COMPILE_INPUT.relative_to(ROOT)),
            str(OVERRIDES.relative_to(ROOT)),
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stderr=subprocess.PIPE,
    )
    diagnostic = completed.stderr or ""
    if completed.returncode != 0:
        raise CompilerFailedError(completed.returncode, diagnostic)
    print(diagnostic, end="", file=sys.stderr)


def regenerate() -> None:
    _guard_python_minor()
    _compile(CONSTRAINTS.relative_to(ROOT))


def check() -> int:
    """Compile to a scratch file, seeded with the committed lock.

    Seeding lets pip-compile reuse already-pinned versions the same way
    an in-place regeneration would, instead of re-resolving unpinned dev
    tool names to whatever is newest at the moment ``--check`` happens to
    run — which would report drift even when no input changed.
    """
    _guard_python_minor()
    with tempfile.TemporaryDirectory() as scratch:
        scratch_file = Path(scratch) / "constraints.txt"
        if CONSTRAINTS.exists():
            scratch_file.write_text(CONSTRAINTS.read_text())
        _compile(scratch_file)
        fresh = scratch_file.read_text().replace(
            str(scratch_file), str(CONSTRAINTS.relative_to(ROOT))
        )
    committed = CONSTRAINTS.read_text() if CONSTRAINTS.exists() else ""
    if fresh == committed:
        return 0
    print(
        "requirements/constraints.txt is stale; run `python tools/lock.py` to refresh.",
        file=sys.stderr,
    )
    return 1


def _run(*, check_only: bool) -> int:
    if check_only:
        return check()
    regenerate()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the lock is up to date without writing",
    )
    args = parser.parse_args(argv)
    try:
        return _run(check_only=args.check)
    except CompilerFailedError as failure:
        print(_without_traceback_frames(failure.diagnostic), file=sys.stderr)
        print(COMPILER_FAILURE_HINT, file=sys.stderr)
        return failure.returncode


if __name__ == "__main__":
    sys.exit(main())
