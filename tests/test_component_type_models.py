from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._cloudaz import _component_type_models as ctm
from nextlabs_sdk._cloudaz._component_type_models import (
    AttributeConfig,
    AttributeDataType,
    ComponentType,
    ComponentTypeType,
    ObligationConfig,
    ObligationRunAt,
    OperatorConfig,
    ParameterConfig,
)
from nextlabs_sdk._cloudaz._models import TagType


@pytest.mark.parametrize(
    "member,expected",
    [
        pytest.param(m, m.name, id=m.name)
        for m in (
            *ComponentTypeType,
            *AttributeDataType,
            *ObligationRunAt,
            *ctm.ObligationParameterType,
        )
    ],
)
def test_enum_member_values_are_self_named(member, expected):
    assert member.value == expected


def test_operator_config_from_api_payload():
    raw = {"id": 5, "key": "!=", "label": "is not", "dataType": "STRING"}
    oc = OperatorConfig.model_validate(raw)
    assert oc.id == 5
    assert oc.key == "!="
    assert oc.label == "is not"
    assert oc.data_type == AttributeDataType.STRING


def test_operator_config_from_python_names():
    oc = OperatorConfig(key="=", label="is", data_type=AttributeDataType.NUMBER)
    assert oc.id is None
    assert oc.data_type == AttributeDataType.NUMBER


def test_operator_config_is_frozen():
    oc = OperatorConfig(key="=", label="is", data_type=AttributeDataType.STRING)
    with pytest.raises(ValidationError):
        oc.key = "changed"  # type: ignore[misc]


def test_attribute_config_from_api_payload():
    raw = {
        "id": 16,
        "name": "Priority",
        "shortName": "priority",
        "dataType": "NUMBER",
        "operatorConfigs": [
            {"id": 1, "key": "=", "label": "=", "dataType": "NUMBER"},
        ],
        "regExPattern": None,
        "sortOrder": 5,
        "version": 4,
    }
    ac = AttributeConfig.model_validate(raw)
    assert ac.id == 16
    assert ac.name == "Priority"
    assert ac.short_name == "priority"
    assert ac.data_type == AttributeDataType.NUMBER
    assert len(ac.operator_configs) == 1
    assert ac.operator_configs[0].key == "="
    assert ac.reg_ex_pattern is None
    assert ac.sort_order == 5
    assert ac.version == 4


def test_attribute_config_from_python_names():
    ac = AttributeConfig(
        name="Category",
        short_name="category",
        data_type=AttributeDataType.STRING,
        sort_order=0,
    )
    assert ac.id is None
    assert ac.operator_configs == []


def test_action_config_from_api_payload():
    raw = {
        "id": 81,
        "name": "View",
        "shortName": "VIEW_TKTS",
        "sortOrder": 0,
        "shortCode": "cc",
        "version": 0,
    }
    ac = ctm.ActionConfig.model_validate(raw)
    assert ac.id == 81
    assert ac.name == "View"
    assert ac.short_name == "VIEW_TKTS"
    assert ac.sort_order == 0
    assert ac.short_code == "cc"


def test_action_config_from_python_names():
    ac = ctm.ActionConfig(name="Edit", short_name="EDIT_TKTS", sort_order=1)
    assert ac.id is None
    assert ac.short_code is None


def test_parameter_config_from_api_payload():
    raw = {
        "id": 1,
        "name": "Ticket Id",
        "shortName": "ticket_id",
        "type": "TEXT_SINGLE_ROW",
        "defaultValue": "${from.ticket_id}",
        "value": "",
        "listValues": None,
        "hidden": False,
        "editable": True,
        "mandatory": True,
        "sortOrder": 0,
    }
    pc = ParameterConfig.model_validate(raw)
    assert pc.id == 1
    assert pc.name == "Ticket Id"
    assert pc.short_name == "ticket_id"
    assert pc.type == ctm.ObligationParameterType.TEXT_SINGLE_ROW
    assert pc.default_value == "${from.ticket_id}"
    assert pc.mandatory is True


def test_obligation_config_from_api_payload():
    raw = {
        "id": 6,
        "name": "Notify Violation",
        "shortName": "notify_violation",
        "runAt": "PEP",
        "parameters": [
            {
                "name": "Ticket Id",
                "shortName": "ticket_id",
                "type": "TEXT_SINGLE_ROW",
                "sortOrder": 0,
            },
        ],
        "sortOrder": 0,
        "daeValidation": "No",
        "version": 4,
    }
    oc = ObligationConfig.model_validate(raw)
    assert oc.id == 6
    assert oc.name == "Notify Violation"
    assert oc.run_at == ObligationRunAt.PEP
    assert len(oc.parameters) == 1
    assert oc.parameters[0].short_name == "ticket_id"
    assert oc.dae_validation == "No"


def _make_full_component_type_data() -> dict[str, object]:
    return {
        "id": 42,
        "name": "Support Tickets",
        "shortName": "support_tickets",
        "description": "Support Tickets Description",
        "type": "RESOURCE",
        "status": "ACTIVE",
        "tags": [
            {
                "id": 21,
                "key": "helpdesk",
                "label": "helpdesk",
                "type": "POLICY_MODEL_TAG",
                "status": "ACTIVE",
            },
        ],
        "attributes": [
            {
                "id": 16,
                "name": "Priority",
                "shortName": "priority",
                "dataType": "NUMBER",
                "operatorConfigs": [
                    {"id": 1, "key": "=", "label": "=", "dataType": "NUMBER"},
                ],
                "regExPattern": None,
                "sortOrder": 0,
            },
        ],
        "actions": [
            {"id": 81, "name": "View", "shortName": "VIEW_TKTS", "sortOrder": 0},
        ],
        "obligations": [
            {
                "id": 6,
                "name": "Notify",
                "shortName": "notify",
                "runAt": "PEP",
                "parameters": [],
                "sortOrder": 0,
            },
        ],
        "version": 1,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "lastUpdatedDate": 1713171640252,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
    }


def test_component_type_from_api_payload():
    ct = ComponentType.model_validate(_make_full_component_type_data())
    assert ct.id == 42
    assert ct.name == "Support Tickets"
    assert ct.short_name == "support_tickets"
    assert ct.description == "Support Tickets Description"
    assert ct.type == ComponentTypeType.RESOURCE
    assert ct.status == "ACTIVE"
    assert len(ct.tags) == 1
    assert ct.tags[0].type == TagType.POLICY_MODEL
    assert len(ct.attributes) == 1
    assert ct.attributes[0].name == "Priority"
    assert len(ct.actions) == 1
    assert ct.actions[0].short_name == "VIEW_TKTS"
    assert len(ct.obligations) == 1
    assert ct.obligations[0].run_at == ObligationRunAt.PEP
    assert ct.version == 1
    assert ct.owner_display_name == "Administrator"
    assert ct.created_date == 1713171640267


def test_component_type_minimal():
    raw = {
        "id": 1,
        "name": "User",
        "shortName": "user",
        "type": "SUBJECT",
        "status": "ACTIVE",
    }
    ct = ComponentType.model_validate(raw)
    assert ct.id == 1
    assert ct.type == ComponentTypeType.SUBJECT
    assert ct.tags == []
    assert ct.attributes == []
    assert ct.actions == []
    assert ct.obligations == []
    assert ct.description is None
    assert ct.version is None


def test_component_type_is_frozen():
    ct = ComponentType.model_validate(_make_full_component_type_data())
    with pytest.raises(ValidationError):
        ct.name = "changed"  # type: ignore[misc]


def test_component_type_rejects_invalid_type():
    with pytest.raises(ValidationError):
        ComponentType.model_validate(
            {
                "id": 1,
                "name": "X",
                "shortName": "x",
                "type": "INVALID",
                "status": "ACTIVE",
            }
        )
