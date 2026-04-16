from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)


def test_audit_log_entry_from_api_payload() -> None:
    raw = {
        "id": 12,
        "timestamp": 1718782853766,
        "action": "LOGOUT",
        "actorId": 0,
        "actor": "Administrator",
        "entityType": "AU",
        "entityId": 0,
        "oldValue": None,
        "newValue": '{"Message":"Administrator has logged out successfully."}',
    }
    entry = AuditLogEntry.model_validate(raw)
    assert entry.id == 12
    assert entry.timestamp == 1718782853766
    assert entry.action == "LOGOUT"
    assert entry.actor_id == 0
    assert entry.actor == "Administrator"
    assert entry.entity_type == "AU"
    assert entry.entity_id == 0
    assert entry.old_value is None
    assert entry.new_value is not None


def test_audit_log_entry_is_frozen() -> None:
    entry = AuditLogEntry.model_validate(
        {
            "id": 1,
            "timestamp": 100,
            "action": "LOGIN",
            "actorId": 0,
            "actor": "Admin",
            "entityType": "AU",
            "entityId": 0,
        }
    )
    with pytest.raises(ValidationError):
        entry.action = "LOGOUT"  # type: ignore[misc]


def test_audit_log_entry_optional_fields_default_to_none() -> None:
    raw = {
        "id": 1,
        "timestamp": 100,
        "action": "LOGIN",
        "actorId": 0,
        "actor": "Admin",
        "entityType": "AU",
        "entityId": 0,
    }
    entry = AuditLogEntry.model_validate(raw)
    assert entry.old_value is None
    assert entry.new_value is None


def test_audit_log_query_serializes_to_api_format() -> None:
    query = AuditLogQuery(
        start_date=1716825600000,
        end_date=1717516799999,
        action="LOGIN",
        entity_type="AU",
        page_number=0,
        page_size=10,
    )
    payload = query.model_dump(by_alias=True, exclude_none=True)
    assert payload["startDate"] == 1716825600000
    assert payload["endDate"] == 1717516799999
    assert payload["action"] == "LOGIN"
    assert payload["entityType"] == "AU"
    assert payload["pageNumber"] == 0
    assert payload["pageSize"] == 10


def test_audit_log_query_excludes_none_fields() -> None:
    query = AuditLogQuery(
        start_date=1716825600000,
        end_date=1717516799999,
    )
    payload = query.model_dump(by_alias=True, exclude_none=True)
    assert "action" not in payload
    assert "entityType" not in payload
    assert "usernames" not in payload
    assert "startDate" in payload
    assert "endDate" in payload


def test_audit_log_query_with_usernames() -> None:
    query = AuditLogQuery(
        start_date=100,
        end_date=200,
        usernames=["admin", "testuser"],
    )
    payload = query.model_dump(by_alias=True, exclude_none=True)
    assert payload["usernames"] == ["admin", "testuser"]


def test_export_request_with_ids() -> None:
    req = ExportAuditLogsRequest(ids=[5, 10, 15])
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert payload["ids"] == [5, 10, 15]
    assert "query" not in payload


def test_export_request_with_query() -> None:
    query = AuditLogQuery(start_date=100, end_date=200, action="LOGIN")
    req = ExportAuditLogsRequest(query=query)
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert "ids" not in payload
    assert payload["query"]["startDate"] == 100
    assert payload["query"]["action"] == "LOGIN"


def test_audit_log_user_from_api_payload() -> None:
    raw = {"firstName": "Test", "lastName": "User", "username": "testuser"}
    user = AuditLogUser.model_validate(raw)
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.username == "testuser"


def test_audit_log_user_is_frozen() -> None:
    user = AuditLogUser.model_validate(
        {"firstName": "A", "lastName": "B", "username": "ab"}
    )
    with pytest.raises(ValidationError):
        user.username = "changed"  # type: ignore[misc]
