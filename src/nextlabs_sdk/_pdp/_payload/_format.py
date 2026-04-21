"""Public value types for the PDP payload loader."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from nextlabs_sdk._pdp._request_models import EvalRequest, PermissionsRequest


class PayloadFormat(str, Enum):
    """Explicit payload-format override passed to the loader / CLI."""

    AUTO = "auto"
    YAML = "yaml"
    JSON = "json"
    XACML_JSON = "xacml"


@dataclass(frozen=True)
class LoadedPayload:
    """Result of :func:`load_eval_payload` / :func:`load_permissions_payload`.

    Exactly one of ``request`` / ``body`` is populated, matching ``kind``.
    """

    kind: Literal["structured", "raw_xacml"]
    request: EvalRequest | PermissionsRequest | None = None
    body: dict[str, object] | None = None

    @classmethod
    def structured(
        cls,
        request: EvalRequest | PermissionsRequest,
    ) -> LoadedPayload:
        return cls(kind="structured", request=request)

    @classmethod
    def raw_xacml(cls, body: dict[str, object]) -> LoadedPayload:
        return cls(kind="raw_xacml", body=body)
