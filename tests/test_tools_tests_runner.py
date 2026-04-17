"""Tests for the ``tools/tests.py`` marker-argument builder.

The script lives under ``tools/`` (excluded from pytest's ``norecursedirs``),
so we load it as a standalone module to exercise the pure helper logic.
"""

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


def test_default_excludes_e2e_marker() -> None:
    argv: list[str] = []

    extra = tests_runner._build_marker_args(argv)

    assert extra == ["-m", "not e2e"]
    assert "E2E_COLLECT" not in os.environ


def test_default_with_no_cov_appends_flag() -> None:
    argv = ["--no-cov"]

    extra = tests_runner._build_marker_args(argv)

    assert extra == ["-m", "not e2e", "--no-cov"]
    assert argv == []


def test_e2e_flag_selects_e2e_and_disables_coverage() -> None:
    argv = ["--e2e"]

    extra = tests_runner._build_marker_args(argv)

    assert extra == ["-m", "e2e", "--no-cov"]
    assert os.environ.get("E2E_COLLECT") == "1"
    assert argv == []


def test_all_flag_selects_everything_with_coverage() -> None:
    argv = ["--all"]

    extra = tests_runner._build_marker_args(argv)

    assert extra == ["-m", "e2e or not e2e"]
    assert os.environ.get("E2E_COLLECT") == "1"
    assert argv == []


def test_all_flag_with_no_cov_disables_coverage() -> None:
    argv = ["--all", "--no-cov"]

    extra = tests_runner._build_marker_args(argv)

    assert extra == ["-m", "e2e or not e2e", "--no-cov"]
    assert os.environ.get("E2E_COLLECT") == "1"
    assert argv == []


def test_all_and_e2e_are_mutually_exclusive() -> None:
    argv = ["--all", "--e2e"]

    with pytest.raises(SystemExit) as exc_info:
        tests_runner._build_marker_args(argv)

    assert exc_info.value.code == 2
