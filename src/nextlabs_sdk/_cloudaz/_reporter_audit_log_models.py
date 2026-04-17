from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReporterAuditLogEntry(BaseModel):
    """A single Reporter audit log record."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    component: str
    created_by: int = Field(alias="createdBy")
    created_date: int = Field(alias="createdDate")
    hidden: bool
    last_updated: int = Field(alias="lastUpdated")
    last_updated_by: int = Field(alias="lastUpdatedBy")
    msg_code: str = Field(alias="msgCode")
    msg_params: str = Field(alias="msgParams")
    owner_display_name: str = Field(alias="ownerDisplayName")
    activity_msg: str = Field(alias="activityMsg")
