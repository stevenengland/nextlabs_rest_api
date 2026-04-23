from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz._models import Operator, Tag, TagType


def test_operator_from_api_payload() -> None:
    raw = {"id": 1, "key": "eq", "label": "Equal", "dataType": "STRING"}
    op = Operator.model_validate(raw)
    assert op.id == 1
    assert op.key == "eq"
    assert op.label == "Equal"
    assert op.data_type == "STRING"


def test_operator_from_python_names() -> None:
    op = Operator(id=2, key="neq", label="Not Equal", data_type="NUMBER")
    assert op.id == 2
    assert op.data_type == "NUMBER"


def test_operator_is_frozen() -> None:
    op = Operator(id=1, key="eq", label="Equal", data_type="STRING")
    with pytest.raises(ValidationError):
        op.key = "changed"  # type: ignore[misc]


def test_tag_type_values() -> None:
    assert TagType.POLICY_MODEL.value == "POLICY_MODEL_TAG"
    assert TagType.COMPONENT.value == "COMPONENT_TAG"
    assert TagType.POLICY.value == "POLICY_TAG"
    assert TagType.FOLDER.value == "FOLDER_TAG"


def test_tag_accepts_folder_type() -> None:
    tag = Tag.model_validate(
        {
            "id": 7,
            "key": "folder",
            "label": "Folder",
            "type": "FOLDER_TAG",
            "status": "ACTIVE",
        },
    )
    assert tag.type == TagType.FOLDER


def test_tag_from_api_payload() -> None:
    raw = {
        "id": 10,
        "key": "dept",
        "label": "Department",
        "type": "COMPONENT_TAG",
        "status": "ACTIVE",
    }
    tag = Tag.model_validate(raw)
    assert tag.id == 10
    assert tag.key == "dept"
    assert tag.label == "Department"
    assert tag.type == TagType.COMPONENT
    assert tag.status == "ACTIVE"


def test_tag_from_python_names() -> None:
    tag = Tag(
        id=20,
        key="env",
        label="Environment",
        type=TagType.POLICY,
        status="ACTIVE",
    )
    assert tag.type == TagType.POLICY


def test_tag_is_frozen() -> None:
    tag = Tag(
        id=1,
        key="k",
        label="L",
        type=TagType.COMPONENT,
        status="ACTIVE",
    )
    with pytest.raises(ValidationError):
        tag.key = "changed"  # type: ignore[misc]


def test_operator_rejects_missing_fields() -> None:
    with pytest.raises(ValidationError):
        Operator.model_validate({"id": 1, "key": "eq"})


def test_tag_accepts_empty_payload() -> None:
    tag = Tag.model_validate({})
    assert tag.id is None
    assert tag.key is None
    assert tag.label is None
    assert tag.type is None
    assert tag.status is None


def test_tag_accepts_partial_payload() -> None:
    tag = Tag.model_validate({"key": "dept", "status": "ACTIVE"})
    assert tag.key == "dept"
    assert tag.status == "ACTIVE"
    assert tag.id is None
    assert tag.label is None
    assert tag.type is None


def test_tag_rejects_invalid_type() -> None:
    with pytest.raises(ValidationError):
        Tag.model_validate(
            {
                "id": 1,
                "key": "k",
                "label": "L",
                "type": "INVALID",
                "status": "ACTIVE",
            }
        )
