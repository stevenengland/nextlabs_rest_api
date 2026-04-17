from __future__ import annotations

from pathlib import Path

import pytest

from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
from nextlabs_sdk._cli._account_resolver import (
    build_active_store,
    build_file_cache,
    resolve_account,
)
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat


def _ctx(
    *,
    base_url: str | None = None,
    username: str | None = None,
    client_id: str = "ControlCenterOIDCClient",
    cache_dir: str | None = None,
) -> CliContext:
    return CliContext(
        base_url=base_url,
        username=username,
        password=None,
        client_id=client_id,
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=None,
        timeout=30.0,
        cache_dir=cache_dir,
    )


def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def test_explicit_flags_win(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    build_active_store(_ctx()).save(
        ActiveAccount(
            base_url="https://pointer.example.com",
            username="pointer-user",
            client_id="pointer-client",
        ),
    )
    ctx = _ctx(
        base_url="https://flag.example.com",
        username="flag-user",
        client_id="flag-client",
    )

    resolved = resolve_account(ctx)

    assert resolved is not None
    assert resolved.base_url == "https://flag.example.com"
    assert resolved.username == "flag-user"
    assert resolved.client_id == "flag-client"


def test_active_pointer_fills_when_flags_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    build_active_store(_ctx()).save(
        ActiveAccount(
            base_url="https://pointer.example.com",
            username="pointer-user",
            client_id="pointer-client",
        ),
    )

    resolved = resolve_account(_ctx())

    assert resolved is not None
    assert resolved.base_url == "https://pointer.example.com"
    assert resolved.username == "pointer-user"
    assert resolved.client_id == "pointer-client"


def test_active_pointer_fills_only_missing_pieces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    build_active_store(_ctx()).save(
        ActiveAccount(
            base_url="https://pointer.example.com",
            username="pointer-user",
            client_id="pointer-client",
        ),
    )

    resolved = resolve_account(_ctx(username="explicit-user"))

    assert resolved is not None
    assert resolved.base_url == "https://pointer.example.com"
    assert resolved.username == "explicit-user"


def test_no_flags_no_pointer_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate(tmp_path, monkeypatch)
    assert resolve_account(_ctx()) is None


def test_cache_dir_from_ctx_is_honoured(tmp_path: Path) -> None:
    custom = tmp_path / "custom-cache"
    ctx = _ctx(cache_dir=str(custom))
    build_active_store(ctx).save(
        ActiveAccount(
            base_url="https://pointer.example.com",
            username="pointer-user",
            client_id="pointer-client",
        ),
    )

    assert (custom / "active_account.json").exists()
    resolved = resolve_account(ctx)
    assert resolved is not None
    assert resolved.username == "pointer-user"


def test_build_file_cache_respects_cache_dir(tmp_path: Path) -> None:
    cache = build_file_cache(_ctx(cache_dir=str(tmp_path)))
    assert cache.path == tmp_path / "tokens.json"
