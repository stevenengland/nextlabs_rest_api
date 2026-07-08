"""Library-only import must not require the optional scim2 dependency."""

from __future__ import annotations

import builtins
import importlib
import sys

import pytest

from nextlabs_sdk.exceptions import SearchExpressionError

_WHERE_MODULE = "nextlabs_sdk._cloudaz._search.where"
_FIELD_MODULE = "nextlabs_sdk._cloudaz._search.field_expr"


def _block_scim2(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "scim2_filter_parser" or name.startswith("scim2_filter_parser."):
            raise ModuleNotFoundError(f"No module named {name!r}")
        return real_import(name, globals, locals, fromlist, level)

    for cached in list(sys.modules):
        if cached == "scim2_filter_parser" or cached.startswith("scim2_filter_parser."):
            monkeypatch.delitem(sys.modules, cached, raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_where_module_imports_without_scim2(monkeypatch):
    # given scim2-filter-parser is not installed
    _block_scim2(monkeypatch)
    monkeypatch.delitem(sys.modules, _WHERE_MODULE, raising=False)

    # when the where module is imported
    module = importlib.import_module(_WHERE_MODULE)

    # then import succeeds and still exposes the public entry point
    assert hasattr(module, "transpile_where")


def test_transpile_where_without_scim2_raises_friendly_error(monkeypatch):
    # given the where module is loaded while scim2 is unavailable
    _block_scim2(monkeypatch)
    monkeypatch.delitem(sys.modules, _WHERE_MODULE, raising=False)
    module = importlib.import_module(_WHERE_MODULE)

    # when a --where filter is transpiled
    with pytest.raises(SearchExpressionError) as excinfo:
        module.transpile_where('name eq "x"')

    # then the error points the user at the optional [cli] extra
    assert "nextlabs-sdk[cli]" in str(excinfo.value)


def test_parse_field_expr_works_without_scim2(monkeypatch):
    # given scim2-filter-parser is not installed
    _block_scim2(monkeypatch)
    monkeypatch.delitem(sys.modules, _FIELD_MODULE, raising=False)

    # when a --field expression is parsed
    module = importlib.import_module(_FIELD_MODULE)
    parsed = module.parse_field_expr("status=DRAFT")

    # then it succeeds without the scim2 dependency
    assert parsed.field == "status"
