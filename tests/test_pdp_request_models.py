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


def test_subject_with_id_only() -> None:
    subject = Subject(id="user@example.com")

    assert subject.id == "user@example.com"
    assert subject.attributes == {}
    assert subject.model_extra == {}


def test_subject_with_extra_kwargs() -> None:
    subject = Subject(id="user@example.com", department="IT", level=3)

    assert subject.id == "user@example.com"
    assert subject.model_extra == {"department": "IT", "level": 3}


def test_subject_with_attributes_dict() -> None:
    subject = Subject(
        id="user@example.com",
        attributes={"custom:vendor:field": "value"},
    )

    assert subject.attributes == {"custom:vendor:field": "value"}


def test_subject_simple_factory() -> None:
    subject = Subject.simple("user@example.com")

    assert subject.id == "user@example.com"
    assert subject.attributes == {}


def test_subject_is_frozen() -> None:
    subject = Subject(id="user@example.com")

    with pytest.raises(ValidationError):
        subject.id = "other"


def test_resource_with_all_fields() -> None:
    resource = Resource(
        id="doc:123",
        type="documents",
        dimension=ResourceDimension.FROM,
        nocache=True,
    )

    assert resource.id == "doc:123"
    assert resource.type == "documents"
    assert resource.dimension == ResourceDimension.FROM
    assert resource.nocache is True


def test_resource_defaults() -> None:
    resource = Resource(id="doc:1", type="docs")

    assert resource.dimension is None
    assert resource.nocache is False
    assert resource.attributes == {}


def test_resource_simple_factory() -> None:
    resource = Resource.simple("doc:123", "documents")

    assert resource.id == "doc:123"
    assert resource.type == "documents"


def test_resource_with_extra_kwargs() -> None:
    resource = Resource(id="doc:1", type="docs", category="security")

    assert resource.model_extra == {"category": "security"}


def test_action_with_id() -> None:
    action = Action(id="VIEW")

    assert action.id == "VIEW"


def test_application_with_id() -> None:
    app = Application(id="my-app")

    assert app.id == "my-app"
    assert app.attributes == {}


def test_application_with_extra_kwargs() -> None:
    app = Application(id="my-app", version="2.0")

    assert app.model_extra == {"version": "2.0"}


def test_environment_with_attributes() -> None:
    env = Environment(attributes={"ip_address": "10.0.0.1"})

    assert env.attributes == {"ip_address": "10.0.0.1"}


def test_environment_with_extra_kwargs() -> None:
    env = Environment(time_of_day="morning")

    assert env.model_extra == {"time_of_day": "morning"}


def test_eval_request_composition() -> None:
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


def test_eval_request_with_environment() -> None:
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


def test_permissions_request_has_no_action() -> None:
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="a"),
    )

    assert not hasattr(request, "action")
    assert request.return_policy_ids is False
    assert request.record_matching_policies is False


def test_permissions_request_with_flags() -> None:
    request = PermissionsRequest(
        subject=Subject(id="u"),
        resource=Resource(id="r", type="t"),
        application=Application(id="a"),
        return_policy_ids=True,
        record_matching_policies=True,
    )

    assert request.return_policy_ids is True
    assert request.record_matching_policies is True
