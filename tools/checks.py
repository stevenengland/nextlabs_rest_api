"""Run quality checks (Black, Flake8, MyPy, Pyright).

Default: live/verbose output (every tool streams to stdout).
`--short`: one-line summary per tool on success; full output only for
failures. Mirrors the convention used by ``tools/tests.py --short``.
"""

import os
import subprocess  # noqa: S404
import sys
from typing import Callable

# A "short" runner captures output and returns (return_code, combined_output).
ToolRunner = Callable[[str, bool], int]


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


def call_black(directory: str, short: bool = False) -> int:
    if not short:
        print("** BLACK **")
    cmd = ["black", directory]
    if short:
        cmd.insert(1, "--quiet")
    try:
        rc, out = (
            _run_captured(cmd)
            if short
            else (
                subprocess.run(cmd, check=False).returncode,  # noqa: S603
                "",
            )
        )
    except FileNotFoundError:
        print("[fail] black not installed")
        return 127
    return _emit_result("black", rc, out, short)


def call_flake8(directory: str, short: bool = False) -> int:
    if not short:
        print("** FLAKE8 **")
    cmd = ["flake8", directory]
    try:
        rc, out = (
            _run_captured(cmd)
            if short
            else (
                subprocess.run(cmd, check=False).returncode,  # noqa: S603
                "",
            )
        )
    except FileNotFoundError:
        print("[fail] flake8 not installed")
        return 127
    return _emit_result("flake8", rc, out, short)


def call_pyright(directory: str, short: bool = False) -> int:
    if not short:
        print("** PYRIGHT (Pylance) **")
    cmd = ["pyright", "--warnings", directory]
    try:
        rc, out = (
            _run_captured(cmd)
            if short
            else (
                subprocess.run(cmd, check=False).returncode,  # noqa: S603
                "",
            )
        )
    except FileNotFoundError:
        print("[fail] pyright not installed")
        return 127
    return _emit_result("pyright", rc, out, short)


def call_mypy(directory: str, short: bool = False) -> int:
    if not short:
        print("** MYPY **")
    cmd = ["mypy", directory, "--cache-dir=/dev/null"]
    env = {**os.environ, "MYPYPATH": "src"}
    try:
        rc, out = (
            _run_captured(cmd, env=env)
            if short
            else (
                subprocess.run(cmd, check=False, env=env).returncode,  # noqa: S603
                "",
            )
        )
    except FileNotFoundError:
        print("[fail] mypy not installed")
        return 127
    return _emit_result("mypy", rc, out, short)


CHECKS: dict[str, ToolRunner] = {
    "black": call_black,
    "flake8": call_flake8,
    "mypy": call_mypy,
    "pyright": call_pyright,
}


def main(argv: list[str]) -> int:
    short = "--short" in argv
    if short:
        argv.remove("--short")

    if argv:
        name = argv[0]
        runner = CHECKS.get(name)
        if runner is None:
            print("Invalid argument. Specify 'black', 'flake8', 'mypy', or 'pyright'.")
            return 2
        return runner(".", short)

    failures = 0
    for runner in CHECKS.values():
        if runner(".", short) != 0:
            failures += 1
    if short:
        print(f"[summary] {len(CHECKS) - failures}/{len(CHECKS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
