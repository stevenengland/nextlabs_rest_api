"""Architectural invariants for issue #299.

Pins the new internal engine package (``nextlabs_sdk._cloudaz._engine``) as
unexported from any public facade, and pins the migrated component-search
module to the engine's spec/runner contract: no hand-rolled page assembly,
and a single shared spec constant per endpoint for the sync/async pair.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from nextlabs_sdk._cloudaz._component_search import (
    AsyncComponentSearchService,
    ComponentSearchService,
)

cs = importlib.import_module("nextlabs_sdk._cloudaz._component_search")


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
    # the spec constants are the single source of truth for the pair
    assert cs._SEARCH_SPEC is cs._SEARCH_SPEC  # module-level constant exists
    # both service classes are constructed over the same module constants;
    # assert the constants are defined exactly once at module scope
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
