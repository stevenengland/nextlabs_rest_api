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


@pytest.mark.parametrize(
    "arg,expected",
    [
        ("tests/unit/test_foo.py", True),
        ("tests/e2e/test_foo.py::TestX::test_y", True),
        ("src/foo.py", True),
        ("some/path", True),
        ("-k", False),
        ("pagination", False),
        ("--short", False),
        ("", False),
    ],
)
def test_looks_like_target(arg, expected):
    assert tests_runner._looks_like_target(arg) is expected


@pytest.mark.parametrize(
    "argv,expected",
    [
        ([], False),
        (["-k", "pagination"], False),
        (["tests/unit/test_foo.py"], True),
        (["-k", "pagination", "tests/unit/"], True),
        (["--no-cov"], False),
        (["path/with/sep"], True),
    ],
)
def test_has_explicit_targets(argv, expected):
    assert tests_runner._has_explicit_targets(argv) is expected


@pytest.mark.parametrize(
    "argv,has_targets,expected_extra,expected_env",
    [
        pytest.param([], True, ["--no-cov"], "1", id="targets-drop-default-marker"),
        pytest.param(
            ["--no-cov"],
            True,
            ["--no-cov"],
            "1",
            id="targets-preserve-no-cov",
        ),
        pytest.param(
            ["--e2e"],
            True,
            ["-m", "e2e", "--no-cov"],
            "1",
            id="targets-plus-e2e-still-applies-e2e-marker",
        ),
    ],
)
def test_build_marker_args_with_targets(
    argv, has_targets, expected_extra, expected_env
):
    extra = tests_runner._build_marker_args(argv, has_targets=has_targets)

    assert extra == expected_extra
    assert os.environ.get("E2E_COLLECT") == expected_env


def test_compose_cmd_drops_root_when_targets_present():
    argv = ["tests/unit/test_foo.py"]
    cmd = tests_runner._compose_cmd(argv, has_targets=True)

    assert "." not in cmd
    assert "tests/unit/test_foo.py" in cmd


def test_compose_cmd_adds_root_when_no_targets():
    argv: list[str] = []
    cmd = tests_runner._compose_cmd(argv, has_targets=False)

    assert "." in cmd
