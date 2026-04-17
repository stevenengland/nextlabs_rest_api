from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _policies_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._component_models import Authority
from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._policy_models import (
    ComponentGroup,
    EnvironmentConfig,
    Policy,
    PolicyObligation,
)


def test_policy_detail_renders_scalar_fields() -> None:
    assert _policies_cmd.policies_app is not None
    policy = Policy(
        id=82,
        folder_id=5,
        name="Allow IT Access",
        full_name="/root/Allow IT Access",
        description="Allow IT dept access",
        status="DRAFT",
        category="access",
        effect_type="ALLOW",
        tags=[
            Tag(id=1, key="dept", label="Dept", type=TagType.POLICY, status="ACTIVE"),
        ],
        parent_id=3,
        parent_name="parent",
        has_parent=True,
        has_sub_policies=False,
        subject_components=[ComponentGroup(operator="AND", components=[])],
        action_components=[ComponentGroup(operator="AND", components=[])],
        from_resource_components=[ComponentGroup(operator="AND", components=[])],
        environment_config=EnvironmentConfig(
            remote_access=1,
            time_since_last_hb_secs=42,
        ),
        expression="attr == true",
        allow_obligations=[
            PolicyObligation(id=1, policy_model_id=2, name="log"),
            PolicyObligation(id=2, policy_model_id=2, name="notify"),
        ],
        attributes=["a", "b", "c"],
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
        version=7,
        authorities=[Authority(authority="admin")],
        manual_deploy=False,
        folder_path="/root",
        component_ids=[11, 12],
        hidden=False,
        deployment_pending=False,
        type="POLICY",
    )
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, color_system=None)
    render_detail(policy, console=console)
    output = buf.getvalue()

    assert "Policy" in output
    assert "82" in output
    assert "Allow IT Access" in output
    assert "Allow IT dept access" in output
    assert "DRAFT" in output
    assert "ALLOW" in output
    assert "access" in output
    assert "Alice" in output
    assert "Bob" in output
    assert "1700000000" in output
    assert "1700000500" in output
    assert "42" in output
    assert "43" in output
    assert "/root" in output
    assert "attr == true" in output
    assert "7" in output
    assert "Tags" in output
    assert "Subject Components" in output
    assert "Allow Obligations" in output
    assert "Attributes" in output
    assert "Authorities" in output
