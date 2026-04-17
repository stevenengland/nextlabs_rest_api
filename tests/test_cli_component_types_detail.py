from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _component_types_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._component_type_models import (
    ActionConfig,
    AttributeConfig,
    AttributeDataType,
    ComponentType,
    ComponentTypeType,
    ObligationConfig,
    ObligationRunAt,
)
from nextlabs_sdk._cloudaz._models import Tag, TagType


def test_component_type_detail_renders_all_scalar_fields() -> None:
    assert _component_types_cmd.component_types_app is not None
    ct = ComponentType(
        id=101,
        name="Document",
        short_name="doc",
        description="Document resource type",
        type=ComponentTypeType.RESOURCE,
        status="ACTIVE",
        tags=[
            Tag(id=1, key="dept", label="Dept", type=TagType.COMPONENT, status="ACTIVE")
        ],
        attributes=[
            AttributeConfig(
                name="classification",
                short_name="cls",
                data_type=AttributeDataType.STRING,
                sort_order=1,
            ),
            AttributeConfig(
                name="owner",
                short_name="own",
                data_type=AttributeDataType.STRING,
                sort_order=2,
            ),
        ],
        actions=[
            ActionConfig(name="read", short_name="r", sort_order=1),
        ],
        obligations=[
            ObligationConfig(
                name="audit",
                short_name="aud",
                run_at=ObligationRunAt.PDP,
                sort_order=1,
            ),
        ],
        version=7,
        owner_id=42,
        owner_display_name="Alice",
        created_date=1_700_000_000,
        last_updated_date=1_700_000_500,
        modified_by_id=43,
        modified_by="Bob",
    )
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, color_system=None)
    render_detail(ct, console=console)
    output = buf.getvalue()

    assert "ComponentType" in output
    assert "101" in output
    assert "Document" in output
    assert "doc" in output
    assert "Document resource type" in output
    assert "RESOURCE" in output
    assert "ACTIVE" in output
    assert "7" in output
    assert "42" in output
    assert "Alice" in output
    assert "1700000000" in output
    assert "1700000500" in output
    assert "43" in output
    assert "Bob" in output
    assert "Tags" in output
    assert "Attributes" in output
    assert "2" in output
    assert "Actions" in output
    assert "Obligations" in output
