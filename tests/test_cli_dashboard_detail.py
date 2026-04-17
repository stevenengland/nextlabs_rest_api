from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _dashboard_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._dashboard_models import PolicyActivity, PolicyDayBucket


def _console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120, color_system=None), buf


def test_policy_activity_detail_renderer_registered_and_renders_fields() -> None:
    assert _dashboard_cmd.dashboard_app is not None
    policy = PolicyActivity(
        policy_name="Access Control Policy",
        policy_decisions=[
            PolicyDayBucket(day_nb=1, allow_count=50, deny_count=3),
            PolicyDayBucket(day_nb=2, allow_count=45, deny_count=7),
        ],
    )
    console, buf = _console()
    render_detail(policy, console=console)
    output = buf.getvalue()
    assert "Policy" in output
    assert "Access Control Policy" in output
    assert "Totals" in output
    assert "allow=95" in output
    assert "deny=10" in output
    assert "total=105" in output
    assert "days=2" in output
    assert "Daily Trend" in output
    assert "day=1" in output
    assert "day=2" in output


def test_policy_activity_detail_renderer_with_empty_decisions() -> None:
    assert _dashboard_cmd.dashboard_app is not None
    policy = PolicyActivity(policy_name="Empty Policy", policy_decisions=[])
    console, buf = _console()
    render_detail(policy, console=console)
    output = buf.getvalue()
    assert "Empty Policy" in output
    assert "allow=0" in output
    assert "deny=0" in output
    assert "days=0" in output
