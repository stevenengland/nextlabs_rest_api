import os
import subprocess  # noqa: S404
import sys


def _extract_no_cov(argv: list[str]) -> bool:
    """Extract standalone --no-cov flag from argv.

    Args:
        argv: Command-line arguments (mutated to remove --no-cov).

    Returns:
        True if --no-cov was present.
    """
    if "--no-cov" in argv:
        argv.remove("--no-cov")
        return True
    return False


def _build_marker_args(argv: list[str]) -> list[str]:
    """Build pytest marker arguments based on test-selection flags.

    Flags:
        - ``--e2e``: run only e2e-marked tests (coverage forced off).
        - ``--all``: run unit and e2e tests in a single run. Coverage
          stays on unless ``--no-cov`` is also passed. Mutually
          exclusive with ``--e2e``.
        - neither: run unit tests only (exclude e2e).

    Args:
        argv: Command-line arguments (mutated to remove consumed flags).

    Returns:
        Extra pytest arguments for marker selection.
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
    extra = ["-m", "not e2e"]
    if no_cov:
        extra.append("--no-cov")
    return extra


def _is_relevant_pytest_line(line: str) -> bool:
    is_coverage = "coverage" in line.lower() and "CoverageWarning" not in line
    is_test_result = "passed" in line or "failed" in line
    is_failure = line.startswith("FAILED") or line.startswith("ERROR")
    return is_failure or is_test_result or is_coverage


def call_pytest_short(argv: list[str]) -> dict[str, str]:
    """Run pytest in short mode with filtered output.

    Args:
        argv: Extra arguments to pass to pytest.

    Returns:
        Dict with 'status' ('passed'/'failed') and 'summary' text.
    """
    marker_args = _build_marker_args(argv)

    cmd = ["python", "-m", "pytest", "."] + marker_args + (argv or [])

    pytest_run = subprocess.run(
        cmd, check=False, capture_output=True, text=True
    )  # noqa: S603

    lines = (pytest_run.stdout + pytest_run.stderr).splitlines()
    keep = [line for line in lines if _is_relevant_pytest_line(line)]

    return {
        "status": "passed" if pytest_run.returncode == 0 else "failed",
        "summary": "\n".join(keep),
    }


def call_pytest(argv: list[str]) -> None:
    """Run pytest with live output.

    Args:
        argv: Extra arguments to pass to pytest.
    """
    marker_args = _build_marker_args(argv)

    print("** PYTEST **")
    cmd_path = "python"
    cmd = [cmd_path, "-m", "pytest", "."] + marker_args
    if argv:
        cmd.extend(argv)
    try:
        subprocess.run(cmd, check=True)  # noqa: S607, S603
    except FileNotFoundError:
        print("Module pytest not found. Please make sure it is installed.")
        exit(1)

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
