"""Run quality checks (Black, Flake8, MyPy, Pyright).

Default: live/verbose output (every tool streams to stdout).
``--short``: one-line summary per tool on success; full output only for
failures. Mirrors the convention used by ``tools/tests.py --short``.

Targeted invocation
-------------------
Positional args select a specific tool and/or narrow the check to specific
paths. ``--short`` / other flags may appear anywhere (parsed before
positional parsing).

Examples::

    # all tools, project-wide (default)
    python tools/checks.py
    python tools/checks.py --short

    # only one tool, project-wide
    python tools/checks.py flake8
    python tools/checks.py --short mypy

    # only one tool, narrowed to paths
    python tools/checks.py flake8 src/foo.py
    python tools/checks.py --short mypy src/foo.py src/bar.py

    # all tools, narrowed to paths
    python tools/checks.py src/foo.py
    python tools/checks.py --short src/foo.py tests/unit/test_foo.py

Disambiguation: the first positional arg is treated as a tool selector iff
it exactly matches one of ``black`` / ``flake8`` / ``mypy`` / ``pyright``.
Otherwise every positional is a path. To pass a file literally named
``black`` etc., prefix with ``./``.

Notes
-----
* ``mypy`` run against explicit paths auto-injects
  ``--follow-imports=silent`` so sibling-import cascades don't spam. Be
  aware that narrowed mypy/pyright runs can miss errors from callers;
  treat them as fast editor-loop feedback, not a merge gate.
"""

import os
import subprocess  # noqa: S404
import sys
from typing import Callable

ToolRunner = Callable[[list[str], bool], int]


def _run_captured(cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
    """Run ``cmd`` capturing stdout+stderr; return (returncode, combined text)."""
    proc = subprocess.run(  # noqa: S603
        cmd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _run_streamed(cmd: list[str], env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(cmd, check=False, env=env)  # noqa: S603
    return proc.returncode


def _emit_result(name: str, rc: int, output: str, short: bool) -> int:
    """Emit one tool's outcome; suppress output on success when ``short``."""
    if rc == 0:
        if short:
            print(f"[ok] {name}")
        else:
            print(f"Calling {name} completed successfully.")
        return 0
    print(f"[fail] {name} (exit {rc})")
    if output.strip():
        print(output.rstrip())
    return rc


def _invoke(
    name: str,
    cmd: list[str],
    short: bool,
    env: dict[str, str] | None = None,
) -> int:
    try:
        if short:
            rc, out = _run_captured(cmd, env=env)
        else:
            rc, out = _run_streamed(cmd, env=env), ""
    except FileNotFoundError:
        print(f"[fail] {name} not installed")
        return 127
    return _emit_result(name, rc, out, short)


def call_black(paths: list[str], short: bool = False) -> int:
    if not short:
        print("** BLACK **")
    cmd = ["black", *paths]
    if short:
        cmd.insert(1, "--quiet")
    return _invoke("black", cmd, short)


def call_flake8(paths: list[str], short: bool = False) -> int:
    if not short:
        print("** FLAKE8 **")
    cmd = ["flake8", *paths]
    return _invoke("flake8", cmd, short)


def call_pyright(paths: list[str], short: bool = False) -> int:
    if not short:
        print("** PYRIGHT (Pylance) **")
    cmd = ["pyright", "--warnings", *paths]
    return _invoke("pyright", cmd, short)


def call_mypy(paths: list[str], short: bool = False) -> int:
    if not short:
        print("** MYPY **")
    narrowed = paths != ["."]
    cmd = ["mypy", *paths, "--cache-dir=/dev/null"]
    if narrowed:
        cmd.append("--follow-imports=silent")
    env = {**os.environ, "MYPYPATH": "src"}
    return _invoke("mypy", cmd, short, env=env)


CHECKS: dict[str, ToolRunner] = {
    "black": call_black,
    "flake8": call_flake8,
    "mypy": call_mypy,
    "pyright": call_pyright,
}


def _parse_args(argv: list[str]) -> tuple[bool, ToolRunner | None, list[str]]:
    """Parse argv into (short, selected_runner_or_None, paths).

    ``--short`` is stripped anywhere in argv. If the first remaining
    positional is a CHECKS key, it becomes the selected runner; remaining
    positionals are paths. Otherwise all positionals are paths.
    """
    args = list(argv)
    short = False
    if "--short" in args:
        args.remove("--short")
        short = True

    runner: ToolRunner | None = None
    if args and args[0] in CHECKS:
        runner = CHECKS[args[0]]
        args = args[1:]

    paths = args if args else ["."]
    return short, runner, paths


def main(argv: list[str]) -> int:
    short, runner, paths = _parse_args(argv)

    if runner is not None:
        return runner(paths, short)

    failures = 0
    for r in CHECKS.values():
        if r(paths, short) != 0:
            failures += 1
    if short:
        print(f"[summary] {len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
