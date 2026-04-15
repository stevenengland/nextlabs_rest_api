import os
import subprocess  # noqa: S404
import sys


def _build_marker_args(argv: list[str]) -> list[str]:
    """Build pytest marker arguments based on --e2e flag.

    When --e2e is present: run only e2e-marked tests.
    When absent: exclude e2e-marked tests.

    Args:
        argv: Command-line arguments (mutated to remove --e2e).

    Returns:
        Extra pytest arguments for marker selection.
    """
    if "--e2e" in argv:
        argv.remove("--e2e")
        os.environ["E2E_COLLECT"] = "1"
        return ["-m", "e2e", "--no-cov"]
    return ["-m", "not e2e"]


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
