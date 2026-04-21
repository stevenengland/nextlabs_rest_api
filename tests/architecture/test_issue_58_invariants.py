"""Architectural invariants for issue #58 (PDP `auth login --type pdp`).

These guardrails pin the contracts the feature relies on so future
refactors do not silently regress the cache-key format, the persisted
token schema, or the ``ActiveAccount`` migration behavior.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._cli._account_menu import AccountIdentifier, cache_key_for
from nextlabs_sdk._cli._cache_key import parse_cache_key

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "nextlabs_sdk"
_CACHED_TOKEN_FILE = _SRC_ROOT / "_auth" / "_token_cache" / "_cached_token.py"


def test_cache_key_is_four_segments_for_cloudaz() -> None:
    account = AccountIdentifier(
        base_url="https://cloudaz.example",
        username="alice",
        client_id="ControlCenterOIDCClient",
        kind="cloudaz",
    )

    key = cache_key_for(account)

    assert key.count("|") == 3


def test_cache_key_is_four_segments_for_pdp() -> None:
    account = AccountIdentifier(
        base_url="https://pdp.example",
        username="",
        client_id="pdp-client",
        kind="pdp",
    )

    key = cache_key_for(account)

    assert key.count("|") == 3


def test_cached_token_has_client_secret_field_and_schema_v3() -> None:
    tree = ast.parse(_CACHED_TOKEN_FILE.read_text(encoding="utf-8"))

    class_node = _find_class(tree, "CachedToken")
    field_names = _dataclass_field_names(class_node)
    assert "client_secret" in field_names

    schema_value = _find_module_constant(tree, "_SCHEMA_VERSION")
    assert schema_value == 3


def test_legacy_three_segment_cache_key_parses_as_cloudaz() -> None:
    parsed = parse_cache_key("https://x/cas/oidc/accessToken|u|c")

    assert parsed is not None
    assert parsed[-1] == "cloudaz"


def test_active_account_tolerates_missing_kind() -> None:
    account = ActiveAccount.from_dict(
        {
            "base_url": "https://cloudaz.example",
            "username": "alice",
            "client_id": "ControlCenterOIDCClient",
        },
    )

    assert account.kind == "cloudaz"


def test_no_type_ignore_or_noqa_in_edited_sources() -> None:
    forbidden = ("# type: ignore", "# noqa")
    edited_files = (
        _SRC_ROOT / "_auth" / "_active_account" / "_active_account.py",
        _SRC_ROOT / "_auth" / "_token_cache" / "_cached_token.py",
        _SRC_ROOT / "_cli" / "_account_menu.py",
        _SRC_ROOT / "_cli" / "_account_preferences.py",
        _SRC_ROOT / "_cli" / "_account_resolver.py",
        _SRC_ROOT / "_cli" / "_account_status_label.py",
        _SRC_ROOT / "_cli" / "_auth_cmd.py",
        _SRC_ROOT / "_cli" / "_cache_key.py",
        _SRC_ROOT / "_cli" / "_client_factory.py",
        _SRC_ROOT / "_cli" / "_pdp_login.py",
    )

    offenders: list[str] = []
    for path in edited_files:
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in forbidden):
            offenders.append(str(path.relative_to(_SRC_ROOT)))

    assert not offenders, f"Forbidden suppressions found in: {offenders}"


def _find_class(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"class {name} not found")


def _dataclass_field_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.add(stmt.target.id)
    return names


def _find_module_constant(tree: ast.Module, name: str) -> object:
    for stmt in tree.body:
        literal = _constant_value(stmt, name)
        if literal is not _NOT_FOUND:
            return literal
    raise AssertionError(f"module constant {name} not found")


_NOT_FOUND = object()


def _constant_value(stmt: ast.stmt, name: str) -> object:
    if isinstance(stmt, ast.Assign):
        return _assign_value(stmt, name)
    if isinstance(stmt, ast.AnnAssign):
        return _ann_assign_value(stmt, name)
    return _NOT_FOUND


def _assign_value(stmt: ast.Assign, name: str) -> object:
    for target in stmt.targets:
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(stmt.value)
    return _NOT_FOUND


def _ann_assign_value(stmt: ast.AnnAssign, name: str) -> object:
    if (
        isinstance(stmt.target, ast.Name)
        and stmt.target.id == name
        and stmt.value is not None
    ):
        return ast.literal_eval(stmt.value)
    return _NOT_FOUND
