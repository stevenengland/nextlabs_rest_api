from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FilterField(BaseModel):
    """A single filter field within report criteria."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    operator: str
    value: list[str] | None = None  # noqa: WPS110
    has_multi_value: bool | None = None
    function: str | None = None


class FilterCriteria(BaseModel):
    """User, resource, policy, or other filter criteria."""

    model_config = ConfigDict(populate_by_name=True)

    look_up_field: FilterField | None = None
    fields: list[FilterField] | None = None


class ReportFilterGeneral(BaseModel):
    """General filter settings (date range, log level, decision, action)."""

    model_config = ConfigDict(populate_by_name=True)

    type: str | None = None
    date_mode: str | None = None
    window_mode: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    fields: list[FilterField] | None = None


class ReportFilters(BaseModel):
    """All filter criteria for a report."""

    model_config = ConfigDict(populate_by_name=True)

    general: ReportFilterGeneral | None = None
    user_criteria: FilterCriteria | None = None
    resource_criteria: FilterCriteria | None = None
    policy_criteria: FilterCriteria | None = None
    other_criteria: FilterCriteria | None = None


class ReportOrderBy(BaseModel):
    """Column ordering specification."""

    model_config = ConfigDict(populate_by_name=True)

    col_name: str
    sort_order: str


class ReportCriteria(BaseModel):
    """Full report criteria including filters, headers, ordering, and paging."""

    model_config = ConfigDict(populate_by_name=True)

    filters: ReportFilters | None = None
    header: list[str] | None = None
    order_by: list[ReportOrderBy] | None = None
    pagesize: int | None = None
    max_rows: int | None = None
    grouping_mode: str | None = None
    group_by: list[str] | None = None
