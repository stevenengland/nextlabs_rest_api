from __future__ import annotations

import io
import json
from typing import Any, Callable

import pytest
from _pytest.capture import CaptureFixture
from rich.console import Console

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output import (
    ColumnDef,
    render,
    render_json,
    render_table,
)
from nextlabs_sdk._cloudaz._models import Tag, TagType


def _make_tag() -> Tag:
    return Tag(
        id=10,
        key="dept",
        label="Department",
        type=TagType.COMPONENT,
        status="ACTIVE",
    )


def _make_ctx(*, json_output: bool = False) -> CliContext:
    return CliContext(
        base_url="https://example.com",
        username="u",
        password="p",
        client_id="c",
        client_secret=None,
        pdp_url=None,
        json_output=json_output,
        no_verify=False,
        timeout=30.0,
    )


TAG_COLUMNS = (
    ColumnDef("ID", "id"),
    ColumnDef("Key", "key"),
    ColumnDef("Label", "label"),
    ColumnDef("Type", "type"),
    ColumnDef("Status", "status"),
)


def test_render_table_shows_headers_and_data() -> None:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)

    render_table([_make_tag()], TAG_COLUMNS, console=console)

    output = buf.getvalue()
    for expected in ("ID", "Key", "10", "dept", "Department"):
        assert expected in output


def test_render_table_with_title() -> None:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)

    render_table([_make_tag()], TAG_COLUMNS, title="Tags", console=console)

    assert "Tags" in buf.getvalue()


@pytest.mark.parametrize(
    "payload_factory,extractor",
    [
        pytest.param(
            _make_tag,
            lambda parsed: parsed,
            id="single-model",
        ),
        pytest.param(
            lambda: [_make_tag()],
            lambda parsed: parsed[0],
            id="list-of-models",
        ),
    ],
)
def test_render_json(
    capsys: CaptureFixture[str],
    payload_factory: Callable[[], Any],
    extractor: Callable[[Any], Any],
) -> None:
    render_json(payload_factory())

    parsed = json.loads(capsys.readouterr().out)
    item = extractor(parsed)
    assert item["id"] == 10
    assert item["key"] == "dept"


def test_render_dispatches_to_json_when_flag_set(capsys: CaptureFixture[str]) -> None:
    render(_make_ctx(json_output=True), _make_tag(), TAG_COLUMNS)

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["id"] == 10


def test_render_dispatches_to_table_when_flag_unset(
    capsys: CaptureFixture[str],
) -> None:
    render(_make_ctx(json_output=False), _make_tag(), TAG_COLUMNS)

    assert "dept" in capsys.readouterr().out
