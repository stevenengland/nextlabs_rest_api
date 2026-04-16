from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AuditLogEntry(BaseModel):
    """A single entity audit log record."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    timestamp: int
    action: str
    actor_id: int = Field(alias="actorId")
    actor: str
    entity_type: str = Field(alias="entityType")
    entity_id: int = Field(alias="entityId")
    old_value: str | None = Field(alias="oldValue", default=None)
    new_value: str | None = Field(alias="newValue", default=None)


class AuditLogQuery(BaseModel):
    """Query parameters for entity audit log search."""

    model_config = ConfigDict(populate_by_name=True)

    start_date: int = Field(serialization_alias="startDate")
    end_date: int = Field(serialization_alias="endDate")
    action: str | None = None
    entity_type: str | None = Field(default=None, serialization_alias="entityType")
    usernames: list[str] | None = None
    entity_id: int | None = Field(default=None, serialization_alias="entityId")
    sort_by: str | None = Field(default=None, serialization_alias="sortBy")
    sort_order: str | None = Field(default=None, serialization_alias="sortOrder")
    page_number: int | None = Field(default=None, serialization_alias="pageNumber")
    page_size: int | None = Field(default=None, serialization_alias="pageSize")


class ExportAuditLogsRequest(BaseModel):
    """Request body for exporting audit logs. Provide either ids or query."""

    model_config = ConfigDict(populate_by_name=True)

    ids: list[int] | None = None
    query: AuditLogQuery | None = None


class AuditLogUser(BaseModel):
    """A user who appears in audit log records."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    username: str
