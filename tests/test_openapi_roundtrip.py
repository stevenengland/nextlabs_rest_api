"""Round-trip every OpenAPI example through the SDK's Pydantic models.

For each example body the spec provides, this test:

1. Looks up the Pydantic model the SDK uses for that ``(path, method,
   status)`` triple (see :mod:`tests._openapi.model_registry`).
2. Extracts the inner resource payload (CloudAz envelope: ``body["data"]``;
   PDP or raw: the whole body).
3. Validates each resource with ``model_validate``, then re-serializes
   it with ``model_dump(by_alias=True, exclude_none=True)``, and validates
   a second time. The first validate proves the SDK accepts vendor JSON;
   the second proves the SDK's serialized form is itself a valid request
   body — the core contract round-trip tests exist to enforce.

Cases on :data:`KNOWN_UNPARSEABLE` are xfailed with a reason. Cases
without a registered model surface as ``MissingModel`` failures so they
receive explicit triage rather than silent skip.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from tests._openapi.allowlist import KNOWN_UNPARSEABLE
from tests._openapi.examples import ExampleCase, collect_example_cases
from tests._openapi.model_registry import RegistryMiss, lookup_model
from tests._openapi.placeholders import substitute


class MissingModel(AssertionError):
    """No model is registered for this spec triple — needs triage."""


def _case_id(case: ExampleCase) -> str:
    return f"{case.method.upper()} {case.path} -> {case.status} ({case.content_type})"


def _extract_items(body: Any) -> list[Any]:
    if isinstance(body, dict) and "data" in body and "statusCode" in body:
        inner = body["data"]
    else:
        inner = body
    if isinstance(inner, list):
        return inner
    return [inner]


def _round_trip(item: Any, model: type[BaseModel]) -> None:
    instance = model.model_validate(item)
    dumped = instance.model_dump(by_alias=True, exclude_none=True)
    model.model_validate(dumped)


_CASES = list(collect_example_cases())


@pytest.mark.parametrize("case", _CASES, ids=_case_id)
def test_openapi_example_round_trips(case: ExampleCase) -> None:
    triple = (case.path, case.method, case.status)
    if triple in KNOWN_UNPARSEABLE:
        pytest.xfail(f"allowlisted: {triple}")

    try:
        model = lookup_model(
            path=case.path,
            method=case.method,
            status=case.status,
        )
    except RegistryMiss as exc:
        raise MissingModel(str(exc)) from exc

    try:
        body = json.loads(substitute(case.body))
    except json.JSONDecodeError as exc:
        pytest.fail(f"example body is not valid JSON: {exc}")
    except ValueError as exc:
        pytest.fail(f"example body contains unknown placeholder: {exc}")

    items = _extract_items(body)
    assert items, "example body yielded no items to validate"

    for item in items:
        try:
            _round_trip(item, model)
        except ValidationError as exc:
            pytest.fail(f"round-trip failed for {_case_id(case)}: {exc}")
