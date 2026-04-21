"""Architectural invariants for issue #63 (interactive SSL retry).

Pins the contract that the SSL-retry helper is:

1. Type-based (no locale-sensitive substring matching on SSL messages).
2. Composed locally inside the login commands — it does **not** leak
   into :mod:`nextlabs_sdk._cli._error_handler`.
3. Imported only by the two login call sites (``_auth_cmd`` and
   ``_pdp_login``) inside the SDK source tree.
4. Using an injected ``confirm`` callable — never a bare ``input(``,
   a hard-coded ``click.confirm(``, or a direct ``typer.prompt(``.
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "nextlabs_sdk"
_SSL_RETRY_FILE = _SRC_ROOT / "_cli" / "_ssl_retry.py"
_ERROR_HANDLER_FILE = _SRC_ROOT / "_cli" / "_error_handler.py"
_FORBIDDEN_SUBSTRINGS = ("CERTIFICATE_VERIFY_FAILED", "verify failed")


def _string_constants(tree: ast.AST) -> list[str]:
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_detector_does_not_use_string_matching() -> None:
    tree = ast.parse(_SSL_RETRY_FILE.read_text(encoding="utf-8"))
    for literal in _string_constants(tree):
        for forbidden in _FORBIDDEN_SUBSTRINGS:
            assert forbidden not in literal, (
                f"Found forbidden substring '{forbidden}' "
                f"in string literal: {literal!r}"
            )


def test_error_handler_does_not_import_ssl_retry() -> None:
    source = _ERROR_HANDLER_FILE.read_text(encoding="utf-8")
    assert "_ssl_retry" not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or "_ssl_retry" not in node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "_ssl_retry" not in alias.name


def test_ssl_retry_only_imported_by_login_handlers() -> None:
    expected = {
        _SRC_ROOT / "_cli" / "_auth_cmd.py",
        _SRC_ROOT / "_cli" / "_pdp_login.py",
    }
    importers: set[Path] = set()
    for path in _SRC_ROOT.rglob("*.py"):
        if path == _SSL_RETRY_FILE:
            continue
        if "_ssl_retry" in path.read_text(encoding="utf-8"):
            importers.add(path)
    assert importers == expected, f"Unexpected importers: {importers}"


def test_prompter_uses_injected_confirm() -> None:
    tree = ast.parse(_SSL_RETRY_FILE.read_text(encoding="utf-8"))
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SslRetryPrompter"
    )
    forbidden_callees = {"input", "click.confirm", "typer.prompt"}
    for call in ast.walk(class_node):
        if not isinstance(call, ast.Call):
            continue
        callee = _dotted_name(call.func)
        assert callee not in forbidden_callees, (
            f"SslRetryPrompter must not call {callee} directly; "
            "use the injected confirm callable instead."
        )


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr}"
    return ""
