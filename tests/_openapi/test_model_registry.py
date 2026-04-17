"""Tests for tests._openapi.model_registry."""

from __future__ import annotations

import pytest

from tests._openapi.model_registry import RegistryMiss, lookup_model


def test_lookup_known_component_get() -> None:
    model = lookup_model(
        path="/console/api/v1/component/mgmt/active/{id}",
        method="get",
        status="200",
    )
    assert model.__name__ == "Component"


def test_lookup_unknown_raises_registry_miss() -> None:
    with pytest.raises(RegistryMiss):
        lookup_model(path="/does/not/exist", method="get", status="200")
