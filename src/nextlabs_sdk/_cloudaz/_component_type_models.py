from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from nextlabs_sdk._cloudaz._models import Tag

_ALIAS_SHORT_NAME = "shortName"
_ALIAS_SORT_ORDER = "sortOrder"


class ComponentTypeType(str, Enum):
    SUBJECT = "SUBJECT"
    RESOURCE = "RESOURCE"
    DA_SUBJECT = "DA_SUBJECT"
    DA_RESOURCE = "DA_RESOURCE"


class AttributeDataType(str, Enum):
    STRING = "STRING"
    NUMBER = "NUMBER"
    DATE = "DATE"
    MULTIVAL = "MULTIVAL"
    COLLECTION = "COLLECTION"
    TIME_INTERVAL = "TIME_INTERVAL"


class OperatorConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    key: str
    label: str
    data_type: AttributeDataType = Field(alias="dataType")


class AttributeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    name: str
    short_name: str = Field(alias=_ALIAS_SHORT_NAME)
    data_type: AttributeDataType = Field(alias="dataType")
    operator_configs: list[OperatorConfig] = Field(
        default_factory=list,
        alias="operatorConfigs",
    )
    reg_ex_pattern: str | None = Field(default=None, alias="regExPattern")
    sort_order: int = Field(alias=_ALIAS_SORT_ORDER)
    version: int | None = None


class ActionConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    name: str
    short_name: str = Field(alias=_ALIAS_SHORT_NAME)
    sort_order: int = Field(alias=_ALIAS_SORT_ORDER)
    short_code: str | None = Field(default=None, alias="shortCode")
    version: int | None = None


class ObligationRunAt(str, Enum):
    PEP = "PEP"
    PDP = "PDP"


class ObligationParameterType(str, Enum):
    TEXT_SINGLE_ROW = "TEXT_SINGLE_ROW"
    TEXT_MULTIPLE_ROW = "TEXT_MULTIPLE_ROW"
    LIST = "LIST"


class ParameterConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    name: str
    short_name: str = Field(alias=_ALIAS_SHORT_NAME)
    type: ObligationParameterType  # noqa: WPS125
    default_value: str | None = Field(default=None, alias="defaultValue")
    value: str | None = None  # noqa: WPS110
    list_values: str | None = Field(default=None, alias="listValues")
    hidden: bool = False
    editable: bool = True
    mandatory: bool = False
    sort_order: int = Field(alias=_ALIAS_SORT_ORDER)
    version: int | None = None


class ObligationConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int | None = None  # noqa: WPS125
    name: str
    short_name: str = Field(alias=_ALIAS_SHORT_NAME)
    run_at: ObligationRunAt = Field(alias="runAt")
    parameters: list[ParameterConfig] = Field(default_factory=list)  # noqa: WPS110
    sort_order: int = Field(alias=_ALIAS_SORT_ORDER)
    dae_validation: str | None = Field(default=None, alias="daeValidation")
    version: int | None = None


class ComponentType(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    name: str
    short_name: str = Field(alias=_ALIAS_SHORT_NAME)
    description: str | None = None
    type: ComponentTypeType  # noqa: WPS125
    status: str
    tags: list[Tag] = Field(default_factory=list)
    attributes: list[AttributeConfig] = Field(default_factory=list)
    actions: list[ActionConfig] = Field(default_factory=list)
    obligations: list[ObligationConfig] = Field(default_factory=list)
    version: int | None = None
    owner_id: int | None = Field(default=None, alias="ownerId")
    owner_display_name: str | None = Field(default=None, alias="ownerDisplayName")
    created_date: int | None = Field(default=None, alias="createdDate")
    last_updated_date: int | None = Field(default=None, alias="lastUpdatedDate")
    modified_by_id: int | None = Field(default=None, alias="modifiedById")
    modified_by: str | None = Field(default=None, alias="modifiedBy")
