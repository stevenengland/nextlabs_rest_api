"""Unit tests for the pure diff helpers in tests._openapi.model_parity."""

from __future__ import annotations

from enum import Enum

import pytest
from pydantic import BaseModel, ConfigDict, Field

from tests._openapi.model_parity import (
    Diff,
    EnumDiff,
    SchemaResolutionError,
    enum_diffs,
    inner_data_schema,
    property_diff,
    required_diff,
    resolve_ref,
    response_schema,
)


class _Status(str, Enum):
    OK = "OK"
    BAD = "BAD"


class _Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int  # noqa: WPS125
    name: str
    nickname: str | None = Field(default=None, alias="nickName")
    status: _Status


def test_required_diff_flags_asymmetry() -> None:
    schema = {"required": ["name", "status", "extra"]}
    diff = required_diff(_Model, schema)
    assert diff == Diff(
        only_in_sdk=frozenset(("id",)),
        only_in_spec=frozenset(("extra",)),
    )


def test_required_diff_empty_when_equal() -> None:
    schema = {"required": ["id", "name", "status"]}
    assert required_diff(_Model, schema).is_empty()


def test_property_diff_uses_alias_names() -> None:
    schema: dict[str, object] = {
        "properties": {"id": {}, "name": {}, "nickName": {}, "status": {}},
    }
    assert property_diff(_Model, schema).is_empty()


def test_property_diff_detects_missing_and_extra() -> None:
    schema: dict[str, object] = {
        "properties": {"id": {}, "name": {}, "deprecated": {}},
    }
    diff = property_diff(_Model, schema)
    assert diff.only_in_sdk == frozenset(("nickName", "status"))
    assert diff.only_in_spec == frozenset(("deprecated",))


def test_enum_diffs_reports_missing_sdk_values() -> None:
    schema = {
        "properties": {
            "status": {"enum": ["OK", "BAD", "UGLY"]},
        },
    }
    diffs = enum_diffs(_Model, schema)
    assert diffs == [EnumDiff(field="status", missing_in_sdk=frozenset(("UGLY",)))]


def test_enum_diffs_ignores_pattern_only_fields() -> None:
    schema = {
        "properties": {
            "status": {"pattern": "OK|BAD|FOLDER"},
        },
    }
    assert enum_diffs(_Model, schema) == []


def test_enum_diffs_skips_non_enum_fields() -> None:
    schema = {"properties": {"name": {"enum": ["a", "b"]}}}
    assert enum_diffs(_Model, schema) == []


def test_resolve_ref_follows_local_pointer() -> None:
    spec = {"components": {"schemas": {"Foo": {"type": "object"}}}}
    assert resolve_ref(spec, "#/components/schemas/Foo") == {"type": "object"}


def test_resolve_ref_rejects_non_local() -> None:
    with pytest.raises(SchemaResolutionError):
        resolve_ref({}, "https://example.com/schema")


def test_resolve_ref_raises_on_missing_key() -> None:
    with pytest.raises(SchemaResolutionError):
        resolve_ref({"components": {}}, "#/components/schemas/Missing")


def test_response_schema_follows_single_ref() -> None:
    spec = {
        "paths": {
            "/x": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/R"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "components": {"schemas": {"R": {"title": "R", "properties": {}}}},
    }
    assert response_schema(spec, "/x", "get", "200")["title"] == "R"


def test_inner_data_schema_returns_none_when_wrapper_has_no_data() -> None:
    spec: dict[str, object] = {
        "paths": {
            "/x": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "*/*": {
                                    "schema": {
                                        "properties": {
                                            "statusCode": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    assert inner_data_schema(spec, "/x", "get", "200") is None


def test_inner_data_schema_unwraps_collection_items_ref() -> None:
    spec: dict[str, object] = {
        "paths": {
            "/x": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "*/*": {
                                    "schema": {
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {
                                                    "$ref": "#/components/schemas/Item",
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        "components": {
            "schemas": {"Item": {"title": "Item", "properties": {"id": {}}}},
        },
    }
    assert inner_data_schema(spec, "/x", "get", "200") == {
        "title": "Item",
        "properties": {"id": {}},
    }
