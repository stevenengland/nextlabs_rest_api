from __future__ import annotations

import io
import json

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
    tag = _make_tag()

    render_table([tag], TAG_COLUMNS, console=console)

    output = buf.getvalue()
    assert "ID" in output
    assert "Key" in output
    assert "10" in output
    assert "dept" in output
    assert "Department" in output


def test_render_table_with_title() -> None:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    tag = _make_tag()

    render_table([tag], TAG_COLUMNS, title="Tags", console=console)

    output = buf.getvalue()
    assert "Tags" in output


def test_render_json_single_model(capsys: CaptureFixture[str]) -> None:
    tag = _make_tag()

    render_json(tag)

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["id"] == 10
    assert parsed["key"] == "dept"


def test_render_json_list_of_models(capsys: CaptureFixture[str]) -> None:
    tags = [_make_tag()]

    render_json(tags)

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert parsed[0]["id"] == 10


def test_render_dispatches_to_json_when_flag_set(capsys: CaptureFixture[str]) -> None:
    ctx = _make_ctx(json_output=True)
    tag = _make_tag()

    render(ctx, tag, TAG_COLUMNS)

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["id"] == 10


def test_render_dispatches_to_table_when_flag_unset(
    capsys: CaptureFixture[str],
) -> None:
    ctx = _make_ctx(json_output=False)
    tag = _make_tag()

    render(ctx, tag, TAG_COLUMNS)

    captured = capsys.readouterr()
    assert "dept" in captured.out
