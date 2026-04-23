from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActivityLogQuery(BaseModel):
    """Query parameters for report activity log search.

    Maps to EnforcementQueryDTO in the NextLabs API.
    """

    model_config = ConfigDict(populate_by_name=True)

    policy_decision: str = Field(serialization_alias="policyDecision")
    sort_by: str = Field(serialization_alias="sortBy")
    sort_order: str = Field(serialization_alias="sortOrder")
    field_name: str = Field(serialization_alias="fieldName")
    field_value: str = Field(serialization_alias="fieldValue")
    from_date: int | None = Field(default=None, serialization_alias="fromDate")
    to_date: int | None = Field(default=None, serialization_alias="toDate")
    header: list[str] | None = None
    page: int | None = None
    size: int | None = None


class ActivityLogAttribute(BaseModel):
    """A single attribute in an activity log row detail response."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    value: str | None = None  # noqa: WPS110
    data_type: str = Field(alias="dataType")
    attr_type: str = Field(alias="attrType")
    is_dynamic: bool = Field(alias="isDynamic")
