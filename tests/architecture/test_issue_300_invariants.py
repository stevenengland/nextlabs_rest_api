"""Architectural invariants for issue #300.

Extends the #299 pin to the three remaining classic-envelope services
migrated onto the paginated engine: no hand-rolled page assembly, and a
single shared spec constant per endpoint for each sync/async pair.

Both invariants are checked against runtime objects — the ``PaginatedSpec``
actually bound to a method's returned paginator, and the shared engine
constructor its ``plan_builder`` was built from — rather than by scanning
source text or bytecode names, so a rename or an aliased reference cannot
silently defeat the check.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, cast

import httpx
import pytest

from nextlabs_sdk import AsyncPaginator, SyncPaginator
from nextlabs_sdk._cloudaz._component_type_search import (
    AsyncComponentTypeSearchService,
    ComponentTypeSearchService,
)
from nextlabs_sdk._cloudaz._engine._constructors import (
    _build_query_plan,
    _build_search_plan,
)
from nextlabs_sdk._cloudaz._engine._spec import PaginatedSpec
from nextlabs_sdk.cloudaz import (
    AsyncPolicySearchService,
    AsyncTagService,
    PolicySearchService,
    SearchCriteria,
    TagService,
    TagType,
)

_SANCTIONED_BUILDERS = (_build_query_plan, _build_search_plan)

_Call = Callable[[Any], Any]
_MethodCalls = tuple[tuple[str, _Call], ...]
_ServicePair = tuple[type, type, _MethodCalls]

# Each entry pairs a sync/async service class with representative calls to
# every paginated method. Both classes expose these methods as plain (not
# ``async def``) callables, since building a paginator issues no I/O — so the
# same lambda drives both the sync and the async instance.
_SERVICE_PAIRS: tuple[_ServicePair, ...] = (
    (
        ComponentTypeSearchService,
        AsyncComponentTypeSearchService,
        (
            ("search", lambda svc: svc.search(SearchCriteria())),
            ("list_saved_searches", lambda svc: svc.list_saved_searches("group")),
            (
                "find_saved_search",
                lambda svc: svc.find_saved_search("group", "name"),
            ),
        ),
    ),
    (
        PolicySearchService,
        AsyncPolicySearchService,
        (
            ("search", lambda svc: svc.search(SearchCriteria())),
            (
                "search_named",
                lambda svc: svc.search_named("saved", SearchCriteria()),
            ),
            ("list_saved_searches", lambda svc: svc.list_saved_searches()),
            ("find_saved_search", lambda svc: svc.find_saved_search("name")),
        ),
    ),
    (
        TagService,
        AsyncTagService,
        (("list", lambda svc: svc.list(TagType.COMPONENT)),),
    ),
)


def _spec_of(paginator: SyncPaginator[Any] | AsyncPaginator[Any]) -> PaginatedSpec[Any]:
    """Return the ``PaginatedSpec`` a returned paginator was built from.

    The engine runner returns a paginator wrapping
    ``functools.partial(self._fetch_page, spec, args, page_size)`` (see
    ``_runner.py`` / ``_async_runner.py``), so the spec that actually governs
    a call is recoverable straight from the public method's return value.

    Args:
        paginator: The paginator returned by a service's paginated method.

    Returns:
        The ``PaginatedSpec`` bound to that paginator's fetch closure.
    """
    fetch_page = paginator._fetch_page
    return cast("functools.partial[Any]", fetch_page).args[0]


@pytest.mark.parametrize("sync_service,async_service,calls", _SERVICE_PAIRS)
def test_sync_and_async_calls_share_one_engine_built_spec(
    sync_service: type,
    async_service: type,
    calls: _MethodCalls,
) -> None:
    sync_instance = sync_service(httpx.Client())
    async_instance = async_service(httpx.AsyncClient())
    for method_name, invoke in calls:
        sync_spec = _spec_of(invoke(sync_instance))
        async_spec = _spec_of(invoke(async_instance))

        assert sync_spec is async_spec, (
            f"{sync_service.__name__}.{method_name} and "
            f"{async_service.__name__}.{method_name} must delegate to the "
            "same spec constant"
        )
        assert isinstance(sync_spec.plan_builder, functools.partial), (
            f"{method_name}'s spec must build its request plan via a shared "
            "engine constructor, not a bespoke plan builder"
        )
        assert sync_spec.plan_builder.func in _SANCTIONED_BUILDERS, (
            f"{method_name}'s spec must be produced by "
            "query_paginated()/search_paginated(), not a hand-rolled "
            "per-endpoint builder"
        )
