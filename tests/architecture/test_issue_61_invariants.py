"""Architectural invariants for issue #61 (PDP `--pdp-client-id`).

These guardrails pin the contracts the feature relies on so future
refactors do not silently regress the new CLI option, the resolver
module shape, or the suppression-free policy.
"""

from __future__ import annotations

import ast
from pathlib import Path

from nextlabs_sdk._cli import _pdp_client_id as _resolver_module
from nextlabs_sdk._cli._context import CliContext

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "nextlabs_sdk"
_APP_FILE = _SRC_ROOT / "_cli" / "_app.py"
_RESOLVER_FILE = _SRC_ROOT / "_cli" / "_pdp_client_id.py"


def test_resolver_module_imports_cleanly() -> None:
    assert _resolver_module.resolve_pdp_client_id is not None


def test_cli_context_has_pdp_client_id_field() -> None:
    assert "pdp_client_id" in {
        field.name for field in CliContext.__dataclass_fields__.values()
    }


def test_app_declares_pdp_client_id_option() -> None:
    source = _APP_FILE.read_text(encoding="utf-8")
    assert "--pdp-client-id" in source
    assert "NEXTLABS_PDP_CLIENT_ID" in source


def test_resolver_module_is_single_public_function() -> None:
    tree = ast.parse(_RESOLVER_FILE.read_text(encoding="utf-8"))
    public_funcs = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    assert public_funcs == ["resolve_pdp_client_id"]


def test_no_type_ignore_or_noqa_in_edited_sources() -> None:
    forbidden = ("# type: ignore", "# noqa")
    edited_files = (
        _SRC_ROOT / "_cli" / "_app.py",
        _SRC_ROOT / "_cli" / "_context.py",
        _SRC_ROOT / "_cli" / "_pdp_client_id.py",
        _SRC_ROOT / "_cli" / "_pdp_login.py",
        _SRC_ROOT / "_cli" / "_client_factory.py",
    )

    offenders: list[str] = []
    for path in edited_files:
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in forbidden):
            offenders.append(str(path.relative_to(_SRC_ROOT)))

    assert not offenders, f"Forbidden suppressions found in: {offenders}"
