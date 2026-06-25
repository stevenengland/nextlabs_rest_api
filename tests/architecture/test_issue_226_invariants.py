"""Architectural invariants for issue #226.

Pins the policy-search parser helpers (and their supporting types) onto
the public ``nextlabs_sdk.cloudaz`` surface. User story 12 promises these
transforms as reusable SDK entry points, so programmatic callers must not
have to reach into the internal ``_cloudaz._search`` modules.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize(
    ("public_name", "internal_module", "internal_name"),
    [
        ("transpile_where", "nextlabs_sdk._cloudaz._search.where", "transpile_where"),
        (
            "parse_field_expr",
            "nextlabs_sdk._cloudaz._search.field_expr",
            "parse_field_expr",
        ),
        ("date_value", "nextlabs_sdk._cloudaz._search.dates", "date_value"),
        ("epoch_millis", "nextlabs_sdk._cloudaz._search.dates", "epoch_millis"),
        ("SearchField", "nextlabs_sdk._cloudaz._search", "SearchField"),
        ("SearchFieldType", "nextlabs_sdk._cloudaz._search", "SearchFieldType"),
    ],
)
def test_search_helper_is_publicly_re_exported(
    public_name: str,
    internal_module: str,
    internal_name: str,
) -> None:
    # given the public CloudAz surface and the internal search module
    public = importlib.import_module("nextlabs_sdk.cloudaz")
    internal = importlib.import_module(internal_module)

    # when the helper is resolved from each side
    public_obj = getattr(public, public_name)
    internal_obj = getattr(internal, internal_name)

    # then the public name re-exports the exact internal object
    assert public_obj is internal_obj
    assert public_name in public.__all__
