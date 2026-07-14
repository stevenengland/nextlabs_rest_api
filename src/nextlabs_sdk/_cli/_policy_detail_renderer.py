"""Detail rendering for the ``policies get`` command."""

from __future__ import annotations

from pydantic import BaseModel
from rich.console import Console

from nextlabs_sdk._cli._detail_renderers import register_detail_renderer
from nextlabs_sdk._cloudaz._policy_models import Policy


def _render_policy_detail(model: BaseModel, console: Console) -> None:
    assert isinstance(model, Policy)
    console.print(f"[bold]Policy[/bold] {model.id}")
    deployment_request_label = (
        None if model.deployment_request is None else str(model.deployment_request.id)
    )
    environment_config_label = (
        None
        if model.environment_config is None
        else (
            f"remote_access={model.environment_config.remote_access}, "
            f"time_since_last_hb_secs="
            f"{model.environment_config.time_since_last_hb_secs}"
        )
    )
    scalar_rows: tuple[tuple[str, object], ...] = (
        ("Name", model.name),
        ("Full Name", model.full_name),
        ("Description", model.description),
        ("Status", model.status),
        ("Category", model.category),
        ("Effect Type", model.effect_type),
        ("Type", model.type),
        ("Folder ID", model.folder_id),
        ("Folder Path", model.folder_path),
        ("Parent ID", model.parent_id),
        ("Parent Name", model.parent_name),
        ("Has Parent", model.has_parent),
        ("Has Sub Policies", model.has_sub_policies),
        ("Has To Subject Components", model.has_to_subject_components),
        ("Has To Resource Components", model.has_to_resource_components),
        ("Environment Config", environment_config_label),
        ("Expression", model.expression),
        ("Sub Policy", model.sub_policy),
        ("Action Type", model.action_type),
        ("Deployed", model.deployed),
        ("Deployment Time", model.deployment_time),
        ("Deployment Pending", model.deployment_pending),
        ("Deployment Request", deployment_request_label),
        ("Manual Deploy", model.manual_deploy),
        ("Revision Count", model.revision_count),
        ("Version", model.version),
        ("Hidden", model.hidden),
        ("Skip Validate", model.skip_validate),
        ("Re-Index Now", model.re_index_now),
        ("Skip Adding True Allow Attribute", model.skip_adding_true_allow_attribute),
        ("Owner ID", model.owner_id),
        ("Owner Display Name", model.owner_display_name),
        ("Created Date", model.created_date),
        ("Last Updated Date", model.last_updated_date),
        ("Modified By ID", model.modified_by_id),
        ("Modified By", model.modified_by),
    )
    count_rows: tuple[tuple[str, int], ...] = (
        ("Tags", len(model.tags)),
        ("Subject Components", len(model.subject_components)),
        ("To Subject Components", len(model.to_subject_components)),
        ("Action Components", len(model.action_components)),
        ("From Resource Components", len(model.from_resource_components)),
        ("To Resource Components", len(model.to_resource_components)),
        ("Allow Obligations", len(model.allow_obligations)),
        ("Deny Obligations", len(model.deny_obligations)),
        ("Sub Policy Refs", len(model.sub_policy_refs)),
        ("Attributes", len(model.attributes)),
        ("Authorities", len(model.authorities)),
        ("Deployment Targets", len(model.deployment_targets)),
        (
            "Component IDs",
            0 if model.component_ids is None else len(model.component_ids),
        ),
    )
    for label, scalar_value in scalar_rows:
        console.print(f"  [bold]{label}[/bold]: {scalar_value}")
    for label, count in count_rows:
        console.print(f"  [bold]{label}[/bold]: {count} defined")


register_detail_renderer(Policy, _render_policy_detail)
