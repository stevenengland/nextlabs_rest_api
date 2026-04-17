from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._audit_log_models import (
    AuditLogEntry,
    AuditLogQuery,
    AuditLogUser,
    ExportAuditLogsRequest,
)


def _basic_entry() -> dict[str, object]:
    return {
        "id": 1,
        "timestamp": 100,
        "action": "LOGIN",
        "actorId": 0,
        "actor": "Admin",
        "entityType": "AU",
        "entityId": 0,
    }


def test_audit_log_entry_from_api_payload():
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


def test_audit_log_entry_optional_fields_default_to_none():
    entry = AuditLogEntry.model_validate(_basic_entry())
    assert entry.old_value is None
    assert entry.new_value is None


@pytest.mark.parametrize(
    "model_cls,raw,mutation",
    [
        pytest.param(
            AuditLogEntry,
            _basic_entry(),
            ("action", "LOGOUT"),
            id="audit-log-entry",
        ),
        pytest.param(
            AuditLogUser,
            {"firstName": "A", "lastName": "B", "username": "ab"},
            ("username", "changed"),
            id="audit-log-user",
        ),
    ],
)
def test_frozen_model_rejects_mutation(model_cls, raw, mutation):
    instance = model_cls.model_validate(raw)
    attr, value = mutation
    with pytest.raises(ValidationError):
        setattr(instance, attr, value)


def test_audit_log_query_serializes_to_api_format():
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


def test_audit_log_query_excludes_none_fields():
    query = AuditLogQuery(start_date=1716825600000, end_date=1717516799999)
    payload = query.model_dump(by_alias=True, exclude_none=True)
    assert "action" not in payload
    assert "entityType" not in payload
    assert "usernames" not in payload
    assert "startDate" in payload
    assert "endDate" in payload


def test_audit_log_query_with_usernames():
    query = AuditLogQuery(start_date=100, end_date=200, usernames=["admin", "testuser"])
    payload = query.model_dump(by_alias=True, exclude_none=True)
    assert payload["usernames"] == ["admin", "testuser"]


def test_export_request_with_ids():
    req = ExportAuditLogsRequest(ids=[5, 10, 15])
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert payload["ids"] == [5, 10, 15]
    assert "query" not in payload


def test_export_request_with_query():
    query = AuditLogQuery(start_date=100, end_date=200, action="LOGIN")
    req = ExportAuditLogsRequest(query=query)
    payload = req.model_dump(by_alias=True, exclude_none=True)
    assert "ids" not in payload
    assert payload["query"]["startDate"] == 100
    assert payload["query"]["action"] == "LOGIN"


def test_audit_log_user_from_api_payload():
    raw = {"firstName": "Test", "lastName": "User", "username": "testuser"}
    user = AuditLogUser.model_validate(raw)
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.username == "testuser"
