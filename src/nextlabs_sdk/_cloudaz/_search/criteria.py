from __future__ import annotations

from enum import Enum
from typing import Any

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
    value: dict[str, Any]  # noqa: WPS110
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
    criteria: dict[str, Any] | None = None


_STRING_LABEL = "String"


def _typed_payload(label: str, **entries: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"type": label}
    out.update(entries)
    return out


class SearchCriteria:  # noqa: WPS214
    """Builder for CloudAz search API request payloads."""

    def __init__(self) -> None:
        self._fields: list[dict[str, Any]] = []
        self._sort_fields: list[dict[str, str]] = []
        self._page_no: int = 0
        self._page_size: int = 20

    def filter_type(self, *types: str) -> SearchCriteria:
        self._append_entry(
            "type",
            SearchFieldType.MULTI_EXACT_MATCH,
            _typed_payload(_STRING_LABEL, value=list(types)),
        )
        return self

    def filter_effect_type(self, *effect_types: str) -> SearchCriteria:
        self._append_entry(
            "effectType",
            SearchFieldType.MULTI_EXACT_MATCH,
            _typed_payload(_STRING_LABEL, value=list(effect_types)),
        )
        return self

    def filter_tags(self, *tag_keys: str) -> SearchCriteria:
        self._append_entry(
            "tags",
            SearchFieldType.NESTED_MULTI,
            _typed_payload(_STRING_LABEL, value=list(tag_keys)),
            nestedField="tags.key",
        )
        return self

    def filter_text(
        self,
        text: str,
        *,
        fields: list[str] | None = None,
    ) -> SearchCriteria:
        self._append_entry(
            "text",
            SearchFieldType.TEXT,
            _typed_payload(
                "Text",
                fields=fields or ["name", "description"],
                value=text,
            ),
        )
        return self

    def filter_date(
        self,
        field: str,
        *,
        from_date: int | None = None,
        to_date: int | None = None,
        date_option: str | None = None,
    ) -> SearchCriteria:
        date_entries: dict[str, Any] = {}
        if from_date is not None:
            date_entries["fromDate"] = from_date
        if to_date is not None:
            date_entries["toDate"] = to_date
        if date_option is not None:
            date_entries["dateOption"] = date_option
        self._append_entry(
            field,
            SearchFieldType.DATE,
            _typed_payload("Date", **date_entries),
        )
        return self

    def filter_field(self, field: SearchField) -> SearchCriteria:
        self._fields.append(
            field.model_dump(by_alias=True, exclude_none=True),
        )
        return self

    def filter_group(self, group: str) -> SearchCriteria:
        self._append_entry(
            "group",
            SearchFieldType.SINGLE_EXACT_MATCH,
            _typed_payload(_STRING_LABEL, value=group),
        )
        return self

    def filter_status(self, *statuses: str) -> SearchCriteria:
        self._append_entry(
            "status",
            SearchFieldType.MULTI,
            _typed_payload(_STRING_LABEL, value=list(statuses)),
        )
        return self

    def filter_model_type(self, *types: str) -> SearchCriteria:
        self._append_entry(
            "modelType",
            SearchFieldType.MULTI,
            _typed_payload(_STRING_LABEL, value=list(types)),
        )
        return self

    def filter_exact(self, field: str, match: str) -> SearchCriteria:
        self._append_entry(
            field,
            SearchFieldType.SINGLE_EXACT_MATCH,
            _typed_payload(_STRING_LABEL, value=match),
        )
        return self

    def sort_by(
        self,
        field: str,
        order: SortOrder = SortOrder.DESC,
    ) -> SearchCriteria:
        self._sort_fields.append({"field": field, "order": order.value})
        return self

    def page(self, page_no: int, page_size: int = 20) -> SearchCriteria:
        self._page_no = page_no
        self._page_size = page_size
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "criteria": {
                "fields": list(self._fields),
                "sortFields": list(self._sort_fields),
                "pageNo": self._page_no,
                "pageSize": self._page_size,
            },
        }

    def _append_entry(
        self,
        name: str,
        kind: SearchFieldType,
        payload: dict[str, Any],
        **extra: Any,
    ) -> None:
        entry: dict[str, Any] = {
            "field": name,
            "type": kind.value,
            "value": payload,
        }
        entry.update(extra)
        self._fields.append(entry)
