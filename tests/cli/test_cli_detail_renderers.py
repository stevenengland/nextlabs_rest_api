from __future__ import annotations

import io

from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli._detail_renderers import (
    register_detail_renderer,
    render_detail,
)


class _Dummy(BaseModel):
    id: int
    name: str


class _Other(BaseModel):
    foo: str


def _render_dummy(model: BaseModel, console: Console) -> None:
    assert isinstance(model, _Dummy)
    console.print(f"DUMMY id={model.id} name={model.name}")


def test_render_detail_uses_registered_renderer() -> None:
    register_detail_renderer(_Dummy, _render_dummy)
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_detail(_Dummy(id=1, name="alice"), console=console)
    assert "DUMMY id=1 name=alice" in buf.getvalue()


def test_render_detail_fallback_for_unregistered_model() -> None:
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_detail(_Other(foo="bar"), console=console)
    output = buf.getvalue()
    assert "_Other" in output or "Other" in output
    assert "foo" in output
    assert "bar" in output


def test_render_detail_renders_sequence_with_separators() -> None:
    register_detail_renderer(_Dummy, _render_dummy)
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_detail(
        [_Dummy(id=1, name="alice"), _Dummy(id=2, name="bob")],
        console=console,
    )
    output = buf.getvalue()
    assert "alice" in output
    assert "bob" in output
