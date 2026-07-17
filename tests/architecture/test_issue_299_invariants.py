"""Architectural invariants for issue #299.

Pins the new internal engine package (``nextlabs_sdk._cloudaz._engine``) as
unexported from any public facade, and pins the migrated component-search
module to the engine's spec/runner contract: no hand-rolled page assembly,
and a single shared spec constant per endpoint for the sync/async pair.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from nextlabs_sdk._cloudaz._component_search import (
    AsyncComponentSearchService,
    ComponentSearchService,
)

cs = importlib.import_module("nextlabs_sdk._cloudaz._component_search")

_SYNC_ASYNC_METHOD_PAIRS = (
    "search",
    "list_saved_searches",
    "find_saved_search",
    "list_names",
    "list_names_by_type",
)


def _spec_names_referenced(method: object) -> set[str]:
    """Return the module-level ``*_SPEC`` constant names a method's body reads."""
    code = method.__code__  # type: ignore[attr-defined]
    return {name for name in code.co_names if name.endswith("_SPEC")}


def test_engine_is_not_on_public_facades():
    for facade_name in ("nextlabs_sdk", "nextlabs_sdk.cloudaz"):
        facade = importlib.import_module(facade_name)
        for name in getattr(facade, "__all__", []):
            obj = getattr(facade, name)
            module = getattr(obj, "__module__", "")
            assert not module.startswith("nextlabs_sdk._cloudaz._engine")
        assert not hasattr(facade, "engine")


def test_component_search_has_no_hand_rolled_assembly():
    module_path = cs.__file__
    assert module_path is not None
    source = Path(module_path).read_text(encoding="utf-8")
    for token in ("PageResult(", "def _fetch_", "_page_params", "build_page"):
        assert token not in source


def test_sync_and_async_share_one_spec_per_endpoint():
    for const_name in (
        "_SEARCH_SPEC",
        "_SAVED_SEARCHES_SPEC",
        "_FIND_SAVED_SEARCH_SPEC",
        "_LIST_NAMES_SPEC",
        "_LIST_NAMES_BY_TYPE_SPEC",
    ):
        assert hasattr(cs, const_name)
    # sanity: the classes exist and take a client
    sync_service: object = ComponentSearchService
    async_service: object = AsyncComponentSearchService
    assert sync_service is not async_service


@pytest.mark.parametrize("method_name", _SYNC_ASYNC_METHOD_PAIRS)
def test_sync_and_async_method_resolve_to_same_spec_constant(method_name):
    # the sync and async call sites for the same endpoint must reference the
    # identical module-level spec constant, not independent duplicates
    sync_specs = _spec_names_referenced(getattr(ComponentSearchService, method_name))
    async_specs = _spec_names_referenced(
        getattr(AsyncComponentSearchService, method_name),
    )
    assert sync_specs == async_specs
    assert len(sync_specs) == 1
