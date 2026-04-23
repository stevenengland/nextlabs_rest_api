"""Run pytest with marker presets and optional short mode.

Flags (parsed and stripped from argv before pytest sees it):

``--short``
    Filter pytest output down to failures/summary lines only.
``--e2e``
    Run only ``e2e``-marked tests (coverage forced off).
``--all``
    Run unit + e2e tests in one pass (coverage stays on unless
    ``--no-cov`` is also passed). Mutually exclusive with ``--e2e``.
``--no-cov``
    Disable coverage collection.

Everything else in argv is forwarded to pytest unchanged.

Targeted invocation
-------------------
Positional args that look like test targets (``*.py``, contain ``/`` or
``::``) are forwarded to pytest as-is, and three things change:

1. The default ``-m "not e2e"`` marker is dropped so an explicit
   ``tests/e2e/test_foo.py`` actually runs without also passing ``--e2e``.
2. The hardcoded project root (``.``) is omitted so pytest only collects
   the requested targets.
3. Coverage is auto-disabled (the project-wide 90% gate can't be met
   from a single file). Pass ``--e2e`` / ``--all`` if you want different
   marker behavior on top of this.

``-k EXPR`` is unaffected because ``EXPR`` isn't path-shaped.

Examples::

    # full suite (unit only) with terse output
    python tools/tests.py --short

    # single test by nodeid
    python tools/tests.py --short tests/unit/auth/test_x.py::TestY::test_z

    # e2e file without --e2e (marker auto-dropped)
    python tools/tests.py --short tests/e2e/test_foo.py

    # filter by name; no target path → marker still applies
    python tools/tests.py --short -k "pagination"
"""

import os
import subprocess  # noqa: S404
import sys

from strip_ansi import strip_ansi


def _extract_no_cov(argv: list[str]) -> bool:
    if "--no-cov" in argv:
        argv.remove("--no-cov")
        return True
    return False


def _looks_like_target(arg: str) -> bool:
    """Return True if ``arg`` looks like a pytest path or nodeid.

    Detection is lexical:
    * contains ``::`` (nodeid)
    * ends with ``.py``
    * contains a path separator (``/`` or ``\\``)

    Flag values like ``-k EXPR`` are not matched because ``EXPR``
    typically has none of the above.
    """
    if arg.startswith("-"):
        return False
    return "::" in arg or arg.endswith(".py") or "/" in arg or "\\" in arg


def _has_explicit_targets(argv: list[str]) -> bool:
    return any(_looks_like_target(a) for a in argv)


def _build_marker_args(argv: list[str], has_targets: bool = False) -> list[str]:
    """Build pytest marker/coverage flags based on selection flags.

    When ``has_targets`` is True, no default marker is applied; the caller
    explicitly named targets and the wrapper honors that choice.
    ``--e2e`` / ``--all`` still override marker behavior when present.
    """
    no_cov = _extract_no_cov(argv)
    want_all = "--all" in argv
    want_e2e = "--e2e" in argv
    if want_all and want_e2e:
        print("Error: --all and --e2e are mutually exclusive.")
        sys.exit(2)
    if want_all:
        argv.remove("--all")
        os.environ["E2E_COLLECT"] = "1"
        extra = ["-m", "e2e or not e2e"]
        if no_cov:
            extra.append("--no-cov")
        return extra
    if want_e2e:
        argv.remove("--e2e")
        os.environ["E2E_COLLECT"] = "1"
        return ["-m", "e2e", "--no-cov"]
    if has_targets:
        os.environ["E2E_COLLECT"] = "1"
        return ["--no-cov"]
    extra = ["-m", "not e2e"]
    if no_cov:
        extra.append("--no-cov")
    return extra


def _is_relevant_pytest_line(line: str) -> bool:
    if line.startswith("PASSED"):
        return False
    is_coverage = "coverage" in line.lower() and "CoverageWarning" not in line
    is_test_result = "passed" in line or "failed" in line
    is_failure = line.startswith("FAILED") or line.startswith("ERROR")
    is_error_detail = line.startswith("E   ") or line.startswith(">   ")
    return is_failure or is_test_result or is_coverage or is_error_detail


def _compose_cmd(argv: list[str], has_targets: bool) -> list[str]:
    marker_args = _build_marker_args(argv, has_targets)
    base = ["python", "-m", "pytest"]
    if not has_targets:
        base.append(".")
    return base + ["-rA"] + marker_args + argv


def call_pytest_short(argv: list[str]) -> dict[str, str]:
    has_targets = _has_explicit_targets(argv)
    cmd = _compose_cmd(argv, has_targets)

    pytest_run = subprocess.run(  # noqa: S603
        cmd, check=False, capture_output=True, text=True
    )

    lines = (pytest_run.stdout + pytest_run.stderr).splitlines()
    lines = [strip_ansi(line) for line in lines]
    keep = [line for line in lines if _is_relevant_pytest_line(line)]

    return {
        "status": "passed" if pytest_run.returncode == 0 else "failed",
        "summary": "\n".join(keep),
    }


def call_pytest(argv: list[str]) -> None:
    has_targets = _has_explicit_targets(argv)
    cmd = _compose_cmd(argv, has_targets)
    cmd = [c for c in cmd if c != "-rA"]  # live mode uses pytest defaults

    print("** PYTEST **")
    try:
        subprocess.run(cmd, check=True)  # noqa: S607, S603
    except FileNotFoundError:
        print("Module pytest not found. Please make sure it is installed.")
        sys.exit(1)

    print("Calling PyTest completed successfully.")


if __name__ == "__main__":
    argv = sys.argv[1:]

    if "--short" in argv:
        argv.remove("--short")
        output = call_pytest_short(argv)
        print(output["summary"])
        if output["status"] == "failed":
            sys.exit(1)
    else:
        call_pytest(argv)
