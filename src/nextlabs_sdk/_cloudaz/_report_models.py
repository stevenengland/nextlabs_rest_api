from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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


class SaveInfo(BaseModel):
    """Persistence metadata for a saved report (name, sharing, audience)."""

    model_config = ConfigDict(populate_by_name=True)

    report_name: str | None = None
    report_desc: str | None = None
    report_type: str | None = None
    shared_mode: str | None = None
    user_ids: list[str] | None = None
    group_ids: list[int] | None = None


class ReportCriteria(BaseModel):
    """Full report criteria including filters, headers, ordering, and paging."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    filters: ReportFilters | None = None
    header: list[str] | None = None
    order_by: list[ReportOrderBy] | None = None
    pagesize: int | None = None
    max_rows: int | None = None
    grouping_mode: str | None = None
    group_by: list[str] | None = None
    aggregators: list[FilterField] | None = None
    save_info: SaveInfo | None = None


class ReportWidget(BaseModel):
    """Widget configuration for a report."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: int | None = None  # noqa: WPS125
    key: str | None = None
    name: str
    title: str
    enabled: bool | None = None
    chart_type: str = Field(alias="chartType")
    attribute_name: str = Field(alias="attributeName")
    max_size: int | None = Field(default=None, alias="maxSize")


class PolicyActivityReportRequest(BaseModel):
    """Input for create, modify, and generate operations."""

    model_config = ConfigDict(populate_by_name=True)

    criteria: ReportCriteria
    widgets: list[ReportWidget] | None = None


class DeleteReportsRequest(BaseModel):
    """Input for deleting reports by IDs or query."""

    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    policy_decision: str | None = Field(
        default=None, serialization_alias="policyDecision"
    )
    report_ids: list[int] | None = Field(default=None, serialization_alias="reportIds")
    shared: bool | None = None


class PolicyActivityReport(BaseModel):
    """Summary of a policy activity report (from list, create, modify)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    title: str
    description: str | None = None
    shared_mode: str = Field(alias="sharedMode")
    decision: str
    date_mode: str = Field(alias="dateMode")
    window_mode: str = Field(alias="windowMode")
    start_date: str = Field(alias="startDate")
    end_date: str = Field(alias="endDate")
    last_updated_date: str = Field(alias="lastUpdatedDate")
    type: str  # noqa: WPS125


class PolicyActivityReportDetail(BaseModel):
    """Full detail of a report (criteria + widgets), from get-by-ID."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    criteria: ReportCriteria
    widgets: list[ReportWidget]


class EnforcementEntry(BaseModel):
    """A single enforcement log row."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="allow")

    row_id: int | None = Field(default=None, alias="ROW_ID")
    time: str | None = Field(default=None, alias="TIME")
    user_name: str | None = Field(default=None, alias="USER_NAME")
    from_resource_name: str | None = Field(default=None, alias="FROM_RESOURCE_NAME")
    from_resource_path: str | None = Field(default=None, alias="FROM_RESOURCE_PATH")
    to_resource_name: str | None = Field(default=None, alias="TO_RESOURCE_NAME")
    policy_name: str | None = Field(default=None, alias="POLICY_NAME")
    policy_decision: str | None = Field(default=None, alias="POLICY_DECISION")
    action: str | None = Field(default=None, alias="ACTION")
    action_short_code: str | None = Field(default=None, alias="ACTION_SHORT_CODE")
    log_level: str | None = Field(default=None, alias="LOG_LEVEL")


class EnforcementTimeBucket(BaseModel):
    """A single time bucket in the enforcement trend widget."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    hour: int
    allow_count: int = Field(alias="allowCount")
    deny_count: int = Field(alias="denyCount")
    decision_count: int = Field(alias="decisionCount")


class WidgetData(BaseModel):
    """Widget data returned by widget endpoints."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    enforcements: list[EnforcementTimeBucket] = Field(default_factory=list)


class CachedUser(BaseModel):
    """A cached enforcement user."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    display_name: str = Field(alias="displayName")
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")


class CachedPolicy(BaseModel):
    """A cached policy for report filtering."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    full_name: str = Field(alias="fullName")


class PolicyModelAction(BaseModel):
    """An action associated with a policy model (resource type)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    policy_model_id: int = Field(alias="policyModelId")
    label: str
    short_code: str = Field(alias="shortCode")


class ResourceActions(BaseModel):
    """Policy models grouped by name with their available actions."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    policy_model_actions: dict[str, list[PolicyModelAction]] = Field(
        alias="policyModelActions"
    )


class AttributeMapping(BaseModel):
    """A single attribute-to-column mapping."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    name: str
    mapped_column: str = Field(alias="mappedColumn")
    data_type: str = Field(alias="dataType")
    attr_type: str = Field(alias="attrType")
    is_dynamic: bool = Field(alias="isDynamic")


class AttributeMappings(BaseModel):
    """Attribute mappings grouped by category."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    resource: list[AttributeMapping]
    user: list[AttributeMapping]
    others: list[AttributeMapping]


class UserGroup(BaseModel):
    """A user group for report sharing."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    title: str


class ApplicationUser(BaseModel):
    """An application user for report sharing."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    username: str
