from __future__ import annotations

from nextlabs_sdk._cloudaz._reporter_audit_log_models import ReporterAuditLogEntry


def test_reporter_audit_log_entry_parses_api_payload() -> None:
    entry = ReporterAuditLogEntry.model_validate(
        {
            "id": 1339,
            "component": "REPORTER",
            "createdBy": 0,
            "createdDate": 1746587919483,
            "hidden": False,
            "lastUpdated": 1746587919483,
            "lastUpdatedBy": 0,
            "msgCode": "audit.export.generated.report",
            "msgParams": '["Test Report"]',
            "ownerDisplayName": "Administrator",
            "activityMsg": "exported {0} generated report",
        }
    )

    assert entry.id == 1339
    assert entry.component == "REPORTER"
    assert entry.created_by == 0
    assert entry.created_date == 1746587919483
    assert entry.hidden is False
    assert entry.last_updated == 1746587919483
    assert entry.last_updated_by == 0
    assert entry.msg_code == "audit.export.generated.report"
    assert entry.msg_params == '["Test Report"]'
    assert entry.owner_display_name == "Administrator"
    assert entry.activity_msg == "exported {0} generated report"
