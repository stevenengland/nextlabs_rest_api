from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Pageable(Protocol):
    """The duck-typed search-criteria contract the engine pages over.

    ``search_paginated`` bodies are built from any object exposing this
    pair: ``page`` returns a copy positioned at ``page_no`` and
    ``to_dict`` renders the JSON request body. ``SearchCriteria`` and the
    per-service criteria adapters (audit/activity logs) all satisfy it
    structurally, so the engine never needs their concrete types.
    """

    def page(self, page_no: int) -> Pageable:
        """Return a copy of the criteria positioned at ``page_no``."""
        ...

    def to_dict(self) -> dict[str, object]:
        """Render the criteria as the endpoint's JSON request body."""
        ...
