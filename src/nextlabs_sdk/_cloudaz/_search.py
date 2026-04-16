from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SearchFieldType(str, Enum):
    SINGLE = "SINGLE"
    SINGLE_EXACT_MATCH = "SINGLE_EXACT_MATCH"
    TEXT = "TEXT"
    DATE = "DATE"
    MULTI = "MULTI"
    MULTI_EXACT_MATCH = "MULTI_EXACT_MATCH"
    NESTED = "NESTED"
    NESTED_MULTI = "NESTED_MULTI"


class SortOrder(str, Enum):
    ASC = "ASC"
    DESC = "DESC"


class SortField(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    order: SortOrder


class SearchField(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    type: SearchFieldType  # noqa: WPS125
    value: dict[str, object]  # noqa: WPS110
    nested_field: str | None = Field(default=None, alias="nestedField")


class SavedSearchType(str, Enum):
    COMPONENT = "COMPONENT"
    POLICY = "POLICY"
    POLICY_MODEL_RESOURCE = "POLICY_MODEL_RESOURCE"
    POLICY_MODEL_SUBJECT = "POLICY_MODEL_SUBJECT"


class SavedSearch(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    name: str
    desc: str | None = None
    type: SavedSearchType  # noqa: WPS125
    status: str | None = None
    shared_mode: str | None = Field(default=None, alias="sharedMode")
    criteria: dict[str, object] | None = None
