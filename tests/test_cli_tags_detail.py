from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _tags_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._models import Tag, TagType


def test_tag_detail_renderer_registered_and_renders_fields() -> None:
    assert _tags_cmd.tags_app is not None
    tag = Tag(
        id=42, key="dept", label="Department", type=TagType.COMPONENT, status="ACTIVE"
    )
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, color_system=None)
    render_detail(tag, console=console)
    output = buf.getvalue()
    assert "Tag" in output
    assert "42" in output
    assert "dept" in output
    assert "Department" in output
    assert "ACTIVE" in output
