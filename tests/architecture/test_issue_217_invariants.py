"""Architectural invariants for issue #217 (typer._click private coupling).

Pins the contract that ``_error_handler.py`` contains no reference to
``typer._click`` at all — neither as a bare top-level import, a guarded
import, nor any other usage.  The context object is located via
``inspect.signature`` on the wrapped function, so no Click Context class
identity is needed.
"""

from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "nextlabs_sdk"
_ERROR_HANDLER_FILE = _SRC_ROOT / "_cli" / "_error_handler.py"


def test_no_typer_click_reference_in_error_handler() -> None:
    """Given _error_handler.py source, when scanned for any reference to
    typer._click, then none exists — the private internal module is not
    imported or mentioned in any form.
    """
    source = _ERROR_HANDLER_FILE.read_text(encoding="utf-8")
    assert "typer._click" not in source, (
        "Found 'typer._click' in _error_handler.py — "
        "the file must not reference the private Typer internal module"
    )


def test_context_extracted_via_inspect_signature() -> None:
    """Given _error_handler.py source, when scanned for inspect.signature,
    then it is present — confirming the signature-binding strategy is in use.
    """
    source = _ERROR_HANDLER_FILE.read_text(encoding="utf-8")
    assert "inspect.signature" in source, (
        "Expected 'inspect.signature' in _error_handler.py — "
        "context extraction must use the signature-binding approach"
    )


def test_no_bare_isinstance_on_click_context() -> None:
    """Given _error_handler.py source, when scanned for _ClickContext,
    then it is absent — the private alias is fully removed and not used
    in any isinstance check.
    """
    source = _ERROR_HANDLER_FILE.read_text(encoding="utf-8")
    assert "_ClickContext" not in source, (
        "Found '_ClickContext' in _error_handler.py — "
        "the Click Context class alias must be fully removed"
    )
