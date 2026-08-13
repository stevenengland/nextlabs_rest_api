from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = (
    Path(__file__).resolve().parent.parent
    / ".github"
    / "workflows"
    / "code_testing.yml"
)
REQUIRED_JOB = "check_and_coverage"
COMPILER_PIN = "pip-tools==7.6.1"
LOCK_CHECK = "python tools/lock.py --check"
FULL_DEV_INSTALL = "requirements/dev.txt"


def _workflow() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text())


def _run_scripts(job: dict[str, Any]) -> list[str]:
    return [step.get("run", "") for step in job["steps"]]


def _index_of(scripts: list[str], needle: str) -> int:
    matches = [position for position, script in enumerate(scripts) if needle in script]
    assert len(matches) == 1, f"expected exactly one step running {needle!r}"
    return matches[0]


def _required_job() -> dict[str, Any]:
    return _workflow()["jobs"][REQUIRED_JOB]


def test_lock_check_runs_on_the_pinned_compiler_before_full_install() -> None:
    scripts = _run_scripts(_required_job())

    compiler_install = _index_of(scripts, COMPILER_PIN)
    lock_check = _index_of(scripts, LOCK_CHECK)
    full_install = _index_of(scripts, FULL_DEV_INSTALL)

    assert compiler_install < lock_check < full_install


def test_valid_lock_continues_into_the_unchanged_downstream_steps() -> None:
    scripts = _run_scripts(_required_job())
    lock_check = _index_of(scripts, LOCK_CHECK)

    downstream = [
        "python -m pip install -e . --no-deps",
        "python ./tools/checks.py",
        "python ./tools/tests.py --short --all",
        "python ./tools/build.py",
    ]

    positions = [_index_of(scripts, script) for script in downstream]
    assert positions == sorted(positions)
    assert all(position > lock_check for position in positions)


def test_the_required_job_is_the_only_place_the_lock_is_verified() -> None:
    jobs = _workflow()["jobs"]

    verifying = [
        name
        for name, job in jobs.items()
        if any(LOCK_CHECK in script for script in _run_scripts(job))
    ]

    assert verifying == [REQUIRED_JOB]
    assert jobs[REQUIRED_JOB]["name"] == "Check and Coverage Test"
