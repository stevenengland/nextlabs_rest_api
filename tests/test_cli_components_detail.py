from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _components_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._component_models import (
    Authority,
    Component,
    ComponentCondition,
    ComponentGroupType,
    ComponentStatus,
    PolicyModelRef,
)
from nextlabs_sdk._cloudaz._models import Tag, TagType


def test_component_detail_renders_scalar_fields() -> None:
    assert _components_cmd.components_app is not None
    component = Component(
        id=1,
        folder_id=5,
        name="Host Name",
        description="A host name component",
        tags=[
            Tag(
                id=1, key="dept", label="Dept", type=TagType.COMPONENT, status="ACTIVE"
            ),
        ],
        type=ComponentGroupType.RESOURCE,
        category="network",
        policy_model=PolicyModelRef(id=9, name="Default"),
        conditions=[
            ComponentCondition(attribute="host", operator="eq", value="a"),
            ComponentCondition(attribute="port", operator="eq", value="80"),
        ],
        status=ComponentStatus.APPROVED,
        parent_id=3,
        parent_name="parent",
        deployment_time=123,
        deployed=True,
        action_type="READ",
        revision_count=4,
        owner_id=42,
        owner_display_name="Alice",
        created_date=1_700_000_000,
        modified_by_id=43,
        modified_by="Bob",
        last_updated_date=1_700_000_500,
        hidden=False,
        authorities=[Authority(authority="admin")],
        folder_path="/root",
        pre_created=False,
        version=7,
        has_inactive_sub_components=False,
        deployment_pending=False,
    )
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, color_system=None)
    render_detail(component, console=console)
    output = buf.getvalue()

    assert "Component" in output
    assert "Host Name" in output
    assert "A host name component" in output
    assert "RESOURCE" in output
    assert "APPROVED" in output
    assert "network" in output
    assert "Alice" in output
    assert "Bob" in output
    assert "1700000000" in output
    assert "1700000500" in output
    assert "42" in output
    assert "43" in output
    assert "/root" in output
    assert "7" in output
    assert "Tags" in output
    assert "Conditions" in output
    assert "2 defined" in output
    assert "Authorities" in output
