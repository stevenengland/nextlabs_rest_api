"""Architectural invariants for issue #300.

Extends the #299 pin to the three remaining classic-envelope services
migrated onto the paginated engine: no hand-rolled page assembly, and a
single shared spec constant per endpoint for each sync/async pair.
"""

from __future__ import annotations

import importlib
import types
from pathlib import Path

import pytest

from nextlabs_sdk._cloudaz._component_type_search import (
    AsyncComponentTypeSearchService,
    ComponentTypeSearchService,
)
from nextlabs_sdk._cloudaz._policy_search import (
    AsyncPolicySearchService,
    PolicySearchService,
)
from nextlabs_sdk._cloudaz._tags import AsyncTagService, TagService

_MODULES = (
    "nextlabs_sdk._cloudaz._component_type_search",
    "nextlabs_sdk._cloudaz._policy_search",
    "nextlabs_sdk._cloudaz._tags",
)

_SERVICE_PAIRS = (
    (
        ComponentTypeSearchService,
        AsyncComponentTypeSearchService,
        ("search", "list_saved_searches", "find_saved_search"),
    ),
    (
        PolicySearchService,
        AsyncPolicySearchService,
        ("search", "search_named", "list_saved_searches", "find_saved_search"),
    ),
    (TagService, AsyncTagService, ("list",)),
)


def _spec_names_referenced(method: types.FunctionType) -> set[str]:
    """Return the module-level ``*_SPEC`` constant names a method's body reads."""
    return {name for name in method.__code__.co_names if name.endswith("_SPEC")}


@pytest.mark.parametrize("module_name", _MODULES)
def test_module_has_no_hand_rolled_assembly(module_name: str):
    module = importlib.import_module(module_name)
    module_path = module.__file__
    assert module_path is not None
    source = Path(module_path).read_text(encoding="utf-8")
    for token in ("PageResult(", "def _fetch_", "build_page", "_list_params"):
        assert token not in source


@pytest.mark.parametrize("sync_service,async_service,methods", _SERVICE_PAIRS)
def test_sync_and_async_method_resolve_to_same_spec_constant(
    sync_service: type,
    async_service: type,
    methods: tuple[str, ...],
):
    for method_name in methods:
        sync_specs = _spec_names_referenced(getattr(sync_service, method_name))
        async_specs = _spec_names_referenced(getattr(async_service, method_name))
        assert sync_specs == async_specs
        assert len(sync_specs) == 1
