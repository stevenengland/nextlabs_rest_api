from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _audit_logs_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._cloudaz._audit_log_models import AuditLogEntry


def test_audit_log_entry_detail_renders_scalar_fields() -> None:
    assert _audit_logs_cmd.audit_logs_app is not None
    entry = AuditLogEntry(
        id=101,
        timestamp=1700000000000,
        action="UPDATE",
        actor_id=7,
        actor="alice",
        entity_type="Policy",
        entity_id=555,
        old_value="before",
        new_value="after",
    )
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=False, width=120, color_system=None)
    render_detail(entry, console=console)
    output = buf.getvalue()
    assert "101" in output
    assert "1700000000000" in output
    assert "UPDATE" in output
    assert "alice" in output
    assert "Policy" in output
    assert "555" in output
    assert "before" in output
    assert "after" in output
    assert "Entity Type" in output
    assert "Actor" in output
