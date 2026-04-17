from __future__ import annotations

from importlib import util as importlib_util
import os
from pathlib import Path
from types import ModuleType
from typing import Iterator

import pytest


def _load_tests_runner() -> ModuleType:
    repo_root = Path(__file__).resolve().parent.parent
    module_path = repo_root / "tools" / "tests.py"
    spec = importlib_util.spec_from_file_location("_tools_tests_runner", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tests_runner = _load_tests_runner()


@pytest.fixture(autouse=True)
def _clear_e2e_env() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    prior = os.environ.pop("E2E_COLLECT", None)
    try:
        yield
    finally:
        os.environ.pop("E2E_COLLECT", None)
        if prior is not None:
            os.environ["E2E_COLLECT"] = prior


@pytest.mark.parametrize(
    "argv,expected_extra,expected_env,expected_argv",
    [
        pytest.param(
            [],
            ["-m", "not e2e"],
            None,
            [],
            id="default-excludes-e2e",
        ),
        pytest.param(
            ["--no-cov"],
            ["-m", "not e2e", "--no-cov"],
            None,
            [],
            id="default-with-no-cov-appends-flag",
        ),
        pytest.param(
            ["--e2e"],
            ["-m", "e2e", "--no-cov"],
            "1",
            [],
            id="e2e-flag-selects-e2e-and-disables-coverage",
        ),
        pytest.param(
            ["--all"],
            ["-m", "e2e or not e2e"],
            "1",
            [],
            id="all-flag-selects-everything-with-coverage",
        ),
        pytest.param(
            ["--all", "--no-cov"],
            ["-m", "e2e or not e2e", "--no-cov"],
            "1",
            [],
            id="all-flag-with-no-cov-disables-coverage",
        ),
    ],
)
def test_build_marker_args(argv, expected_extra, expected_env, expected_argv):
    extra = tests_runner._build_marker_args(argv)

    assert extra == expected_extra
    assert argv == expected_argv
    if expected_env is None:
        assert "E2E_COLLECT" not in os.environ
    else:
        assert os.environ.get("E2E_COLLECT") == expected_env


def test_all_and_e2e_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc_info:
        tests_runner._build_marker_args(["--all", "--e2e"])

    assert exc_info.value.code == 2
