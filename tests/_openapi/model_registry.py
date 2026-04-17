"""Map (path, method, status) triples to the SDK's Pydantic response class.

The registry returns the model for the *inner* ``data`` field of a CloudAz
response envelope. The round-trip test extracts ``data`` from the envelope
before validating it against the model returned here.

PDP responses are not envelope-wrapped; for those, the registered model
validates the full body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel


class RegistryMiss(Exception):
    """Raised when no Pydantic model is registered for a given spec triple."""


@dataclass(frozen=True)
class _Entry:
    pattern: str
    method: str
    status: str
    model: type[BaseModel]


def _entries() -> list[_Entry]:
    # Lazy imports — importing this module during collection must not
    # pull in every SDK submodule.
    from nextlabs_sdk._cloudaz._component_models import (
        Component,
        Dependency,
        DeploymentResult,
    )
    from nextlabs_sdk._cloudaz._component_type_models import ComponentType
    from nextlabs_sdk._cloudaz._models import Tag
    from nextlabs_sdk._cloudaz._policy_models import Policy

    return [
        _Entry(
            r"^/console/api/v1/component/mgmt/active/\{id\}$",
            "get",
            "200",
            Component,
        ),
        _Entry(
            r"^/console/api/v1/component/mgmt/\{id\}$",
            "get",
            "200",
            Component,
        ),
        _Entry(
            r"^/console/api/v1/policy/mgmt/active/\{id\}$",
            "get",
            "200",
            Policy,
        ),
        _Entry(r"^/console/api/v1/policy/mgmt/\{id\}$", "get", "200", Policy),
        _Entry(
            r"^/console/api/v1/policyModel/mgmt/active/\{id\}$",
            "get",
            "200",
            ComponentType,
        ),
        _Entry(
            r"^/console/api/v1/policyModel/mgmt/\{id\}$",
            "get",
            "200",
            ComponentType,
        ),
        _Entry(r"^/console/api/v1/config/tags/\{id\}$", "get", "200", Tag),
        _Entry(
            r"^/console/api/v1/config/tags/list/\{type\}$",
            "get",
            "200",
            Tag,
        ),
        _Entry(
            r"^/console/api/v1/component/mgmt/findDependencies$",
            "post",
            "200",
            Dependency,
        ),
        _Entry(
            r"^/console/api/v1/policy/mgmt/findDependencies$",
            "post",
            "200",
            Dependency,
        ),
        _Entry(
            r"^/console/api/v1/component/mgmt/deploy$",
            "post",
            "200",
            DeploymentResult,
        ),
    ]


def lookup_model(
    *,
    path: str,
    method: str,
    status: str,
) -> type[BaseModel]:
    """Find the Pydantic model the SDK uses for this response triple.

    Args:
        path: OpenAPI path template.
        method: Lowercase HTTP method.
        status: HTTP status code as a string.

    Returns:
        The Pydantic class used for the inner ``data`` field (CloudAz) or
        the full body (PDP).

    Raises:
        RegistryMiss: If no entry matches.
    """
    for entry in _entries():
        method_matches = entry.method == method
        status_matches = entry.status == status
        path_matches = re.match(entry.pattern, path) is not None
        if method_matches and status_matches and path_matches:
            return entry.model
    raise RegistryMiss(f"no model for {method.upper()} {path} -> {status}")
