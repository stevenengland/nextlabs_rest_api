from __future__ import annotations

import importlib
from importlib import util as importlib_util

import pytest
from mockito import mock, verify, when

from nextlabs_sdk._cli import _entrypoint


def _stub_find_spec(typer_present: bool, rich_present: bool) -> None:
    typer_spec = object() if typer_present else None
    rich_spec = object() if rich_present else None
    when(importlib_util).find_spec("typer").thenReturn(typer_spec)
    when(importlib_util).find_spec("rich").thenReturn(rich_spec)


@pytest.mark.parametrize(
    "typer_present,rich_present,expected_missing",
    [
        pytest.param(False, True, "missing: typer", id="typer-missing"),
        pytest.param(True, False, "missing: rich", id="rich-missing"),
        pytest.param(False, False, "missing: typer, rich", id="both-missing"),
    ],
)
def test_main_exits_when_deps_missing(
    capsys: pytest.CaptureFixture[str],
    typer_present: bool,
    rich_present: bool,
    expected_missing: str,
):
    _stub_find_spec(typer_present=typer_present, rich_present=rich_present)

    with pytest.raises(SystemExit) as exc_info:
        _entrypoint.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert expected_missing in captured.err
    assert "pip install 'nextlabs-sdk[cli]'" in captured.err


def test_main_delegates_to_app_when_deps_present(
    capsys: pytest.CaptureFixture[str],
):
    _stub_find_spec(typer_present=True, rich_present=True)

    fake_app_module = mock()
    when(fake_app_module).app().thenReturn(None)
    when(importlib).import_module("nextlabs_sdk._cli._app").thenReturn(fake_app_module)

    _entrypoint.main()

    verify(fake_app_module, times=1).app()
    captured = capsys.readouterr()
    assert captured.err == ""
