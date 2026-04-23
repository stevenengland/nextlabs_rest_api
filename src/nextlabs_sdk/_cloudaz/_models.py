from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Operator(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    key: str
    label: str
    data_type: str = Field(alias="dataType")


class TagType(str, Enum):
    POLICY_MODEL = "POLICY_MODEL_TAG"
    COMPONENT = "COMPONENT_TAG"
    POLICY = "POLICY_TAG"
    FOLDER = "FOLDER_TAG"


class Tag(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int  # noqa: WPS125
    key: str
    label: str
    type: TagType  # noqa: WPS125
    status: str
