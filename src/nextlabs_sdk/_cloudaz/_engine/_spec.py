from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from nextlabs_sdk._cloudaz._engine._dialect import PageDialect
from nextlabs_sdk._cloudaz._engine._request_plan import RequestPlan

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True, eq=False)
class PaginatedSpec(Generic[_ModelT]):
    """Endpoint spec describing how to build a request for one page."""

    model: type[_ModelT]
    method: str
    dialect: PageDialect
    plan_builder: Callable[[Mapping[str, object], int, int | None], RequestPlan]
