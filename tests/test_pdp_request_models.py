from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextlabs_sdk._pdp._enums import ResourceDimension
from nextlabs_sdk._pdp._request_models import (
    Action,
    Application,
    Environment,
    EvalRequest,
    PermissionsRequest,
    Resource,
    Subject,
)


@pytest.mark.parametrize(
    "factory,checks",
    [
        pytest.param(
            lambda: Subject(id="user@example.com"),
            {"id": "user@example.com", "attributes": {}, "model_extra": {}},
            id="subject-id-only",
        ),
        pytest.param(
            lambda: Subject(id="user@example.com", department="IT", level=3),
            {"id": "user@example.com", "model_extra": {"department": "IT", "level": 3}},
            id="subject-extra-kwargs",
        ),
        pytest.param(
            lambda: Subject(
                id="user@example.com",
                attributes={"custom:vendor:field": "value"},
            ),
            {"attributes": {"custom:vendor:field": "value"}},
            id="subject-attributes-dict",
        ),
        pytest.param(
            lambda: Subject.simple("user@example.com"),
            {"id": "user@example.com", "attributes": {}},
            id="subject-simple-factory",
        ),
        pytest.param(
            lambda: Resource(
                id="doc:123",
                type="documents",
                dimension=ResourceDimension.FROM,
                nocache=True,
            ),
            {
                "id": "doc:123",
                "type": "documents",
                "dimension": ResourceDimension.FROM,
                "nocache": True,
            },
            id="resource-all-fields",
        ),
        pytest.param(
            lambda: Resource(id="doc:1", type="docs"),
            {"dimension": None, "nocache": False, "attributes": {}},
            id="resource-defaults",
        ),
        pytest.param(
            lambda: Resource.simple("doc:123", "documents"),
            {"id": "doc:123", "type": "documents"},
            id="resource-simple-factory",
        ),
        pytest.param(
            lambda: Resource(id="doc:1", type="docs", category="security"),
            {"model_extra": {"category": "security"}},
            id="resource-extra-kwargs",
        ),
        pytest.param(
            lambda: Action(id="VIEW"),
            {"id": "VIEW"},
            id="action-with-id",
        ),
        pytest.param(
            lambda: Application(id="my-app"),
            {"id": "my-app", "attributes": {}},
            id="application-with-id",
        ),
        pytest.param(
            lambda: Application(id="my-app", version="2.0"),
            {"model_extra": {"version": "2.0"}},
            id="application-extra-kwargs",
        ),
        pytest.param(
            lambda: Environment(attributes={"ip_address": "10.0.0.1"}),
            {"attributes": {"ip_address": "10.0.0.1"}},
            id="environment-with-attributes",
        ),
        pytest.param(
            lambda: Environment(time_of_day="morning"),
            {"model_extra": {"time_of_day": "morning"}},
            id="environment-extra-kwargs",
        ),
    ],
)
def test_model_construction(factory, checks):
    instance = factory()
    for attr, expected in checks.items():
        assert getattr(instance, attr) == expected


def test_subject_is_frozen():
    subject = Subject(id="user@example.com")
    with pytest.raises(ValidationError):
        subject.id = "other"


def test_eval_request_composition():
    request = EvalRequest(
        subject=Subject(id="user@example.com"),
        action=Action(id="VIEW"),
        resource=Resource(id="doc:1", type="docs"),
        application=Application(id="my-app"),
    )

    assert request.subject.id == "user@example.com"
    assert request.action.id == "VIEW"
    assert request.resource.type == "docs"
    assert request.application.id == "my-app"
    assert request.environment is None
    assert request.return_policy_ids is False


def test_eval_request_with_environment():
    request = EvalRequest(
        subject=Subject(id="u"),
        action=Action(id="VIEW"),
        resource=Resource(id="r", type="t"),
        application=Application(id="a"),
        environment=Environment(attributes={"ip": "10.0.0.1"}),
        return_policy_ids=True,
    )

    assert request.environment is not None
    assert request.environment.attributes == {"ip": "10.0.0.1"}
    assert request.return_policy_ids is True


def test_permissions_request_has_no_action():
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="a"),
    )

    assert not hasattr(request, "action")
    assert request.return_policy_ids is False
    assert request.record_matching_policies is False


def test_permissions_request_with_flags():
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="a"),
        return_policy_ids=True,
        record_matching_policies=True,
    )

    assert request.return_policy_ids is True
    assert request.record_matching_policies is True
