from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestPlan:
    """A declarative description of a single HTTP request to issue."""

    method: str
    path: str
    params: dict[str, int] | None = None  # noqa: WPS110
    json: object | None = None
