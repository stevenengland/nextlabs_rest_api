from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import typer

from nextlabs_sdk._auth._token_cache._cached_token import CachedToken
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._account_preferences import AccountPreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._account_resolver import ResolvedAccount
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._pdp._client import PdpClient


def _make_ctx(
    *,
    base_url: str | None = "https://example.com",
    username: str | None = "user",
    password: str | None = "pass",
    client_id: str = "client",
    client_secret: str | None = "secret",
    verify: bool | None = None,
    cache_dir: str | None = None,
) -> CliContext:
    return CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=verify,
        timeout=30.0,
        cache_dir=cache_dir,
    )


@pytest.mark.parametrize(
    "factory,kwargs,match",
    [
        pytest.param(
            _client_factory.make_cloudaz_client,
            {"base_url": None},
            "base-url",
            id="cloudaz-base-url",
        ),
        pytest.param(
            _client_factory.make_cloudaz_client,
            {"username": None},
            "username",
            id="cloudaz-username",
        ),
        pytest.param(
            _client_factory.make_cloudaz_client,
            {"password": None},
            "password",
            id="cloudaz-password",
        ),
        pytest.param(
            _client_factory.make_pdp_client,
            {"base_url": None},
            "base-url",
            id="pdp-base-url",
        ),
        pytest.param(
            _client_factory.make_pdp_client,
            {"client_secret": None},
            "client-secret",
            id="pdp-client-secret",
        ),
    ],
)
def test_factory_raises_when_required_field_missing(factory, kwargs, match):
    with pytest.raises(typer.BadParameter, match=match):
        factory(_make_ctx(**kwargs))


# ─── verify_ssl precedence ─────────────────────────────────────────────────


def _seed_prefs(cache_dir: Path, *, verify_ssl: bool) -> None:
    store = AccountPreferencesStore(path=cache_dir / "account_prefs.json")
    store.save(
        "https://example.com|user|client",
        AccountPreferences(verify_ssl=verify_ssl),
    )


def _verify_passed_to_cloudaz(
    ctx: CliContext,
    monkeypatch: pytest.MonkeyPatch,
) -> bool:
    captured: dict[str, object] = {}

    def _capture(*_args: object, **kwargs: object) -> CloudAzClient:
        captured.update(kwargs)
        return cast(CloudAzClient, object())

    monkeypatch.setattr(_client_factory, "CloudAzClient", _capture)
    _client_factory.make_cloudaz_client(ctx)
    config = captured["http_config"]
    return getattr(config, "verify_ssl")


def _verify_passed_to_pdp(
    ctx: CliContext,
    monkeypatch: pytest.MonkeyPatch,
) -> bool:
    captured: dict[str, object] = {}

    def _capture(*_args: object, **kwargs: object) -> PdpClient:
        captured.update(kwargs)
        return cast(PdpClient, object())

    monkeypatch.setattr(_client_factory, "PdpClient", _capture)
    _client_factory.make_pdp_client(ctx)
    config = captured["http_config"]
    return getattr(config, "verify_ssl")


def test_cloudaz_defaults_to_verify_true_when_no_flag_no_prefs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ctx = _make_ctx(cache_dir=str(tmp_path))
    assert _verify_passed_to_cloudaz(ctx, monkeypatch) is True


def test_cloudaz_uses_persisted_preference_when_flag_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=False)
    ctx = _make_ctx(cache_dir=str(tmp_path))
    assert _verify_passed_to_cloudaz(ctx, monkeypatch) is False


def test_cloudaz_cli_flag_overrides_persisted_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=False)
    ctx = _make_ctx(cache_dir=str(tmp_path), verify=True)
    assert _verify_passed_to_cloudaz(ctx, monkeypatch) is True


def test_cloudaz_cli_no_verify_overrides_persisted_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=True)
    ctx = _make_ctx(cache_dir=str(tmp_path), verify=False)
    assert _verify_passed_to_cloudaz(ctx, monkeypatch) is False


def test_pdp_defaults_to_verify_true_when_no_flag_no_prefs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    ctx = _make_ctx(cache_dir=str(tmp_path))
    assert _verify_passed_to_pdp(ctx, monkeypatch) is True


def test_pdp_uses_persisted_preference_when_flag_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=False)
    ctx = _make_ctx(cache_dir=str(tmp_path))
    assert _verify_passed_to_pdp(ctx, monkeypatch) is False


def test_pdp_cli_flag_overrides_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=False)
    ctx = _make_ctx(cache_dir=str(tmp_path), verify=True)
    assert _verify_passed_to_pdp(ctx, monkeypatch) is True


def test_non_login_cli_flag_does_not_mutate_persisted_preference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_prefs(tmp_path, verify_ssl=False)
    ctx = _make_ctx(cache_dir=str(tmp_path), verify=True)
    _verify_passed_to_cloudaz(ctx, monkeypatch)

    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    entry = store.load("https://example.com|user|client")
    assert entry is not None
    assert entry.verify_ssl is False


# ─── refresh-token-aware pre-flight gate + TTY prompt ──────────────────────


_ACCOUNT = ResolvedAccount(
    base_url="https://example.com",
    username="user",
    client_id="client",
)
_CACHE_KEY = "https://example.com/cas/oidc/accessToken|user|client"


def _isatty_false() -> bool:
    return False


def _isatty_true() -> bool:
    return True


def _seed_token(
    cache_dir: Path,
    *,
    expires_at: float,
    refresh_token: str | None,
    refresh_expires_at: float | None,
) -> None:
    cache = FileTokenCache(path=cache_dir / "tokens.json")
    cache.save(
        _CACHE_KEY,
        CachedToken(
            access_token="at",
            refresh_token=refresh_token,
            expires_at=expires_at,
            token_type="bearer",
            scope=None,
            refresh_expires_at=refresh_expires_at,
        ),
    )


def _capture_cloudaz_kwargs(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    captured: dict[str, object] = {}

    def _capture(*_args: object, **kwargs: object) -> CloudAzClient:
        captured.update(kwargs)
        return cast(CloudAzClient, object())

    monkeypatch.setattr(_client_factory, "CloudAzClient", _capture)
    return captured


def test_gate_accepts_cached_refresh_token_when_access_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_token(
        tmp_path,
        expires_at=0,
        refresh_token="rt",
        refresh_expires_at=10**12,
    )
    captured = _capture_cloudaz_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] is None


def test_gate_accepts_refresh_token_with_unknown_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_token(
        tmp_path,
        expires_at=0,
        refresh_token="rt",
        refresh_expires_at=None,
    )
    captured = _capture_cloudaz_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] is None


def test_gate_rejects_when_refresh_token_known_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_token(
        tmp_path,
        expires_at=0,
        refresh_token="rt",
        refresh_expires_at=0,
    )
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    with pytest.raises(typer.BadParameter, match="password"):
        _client_factory.make_cloudaz_client(ctx)


def test_gate_rejects_when_no_refresh_token_and_access_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_token(
        tmp_path,
        expires_at=0,
        refresh_token=None,
        refresh_expires_at=None,
    )
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    with pytest.raises(typer.BadParameter, match="password"):
        _client_factory.make_cloudaz_client(ctx)


def test_gate_rejects_when_no_cache_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    with pytest.raises(typer.BadParameter, match="password"):
        _client_factory.make_cloudaz_client(ctx)


def test_tty_prompt_supplies_password_when_cache_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_cloudaz_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)
    prompts: list[tuple[str, bool]] = []

    def _fake_prompt(text: str, *, hide_input: bool = False, **_: object) -> str:
        prompts.append((text, hide_input))
        return "typed-pw"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] == "typed-pw"
    assert prompts and prompts[0][1] is True
    assert "user@https://example.com" in prompts[0][0]


def test_non_tty_raises_bad_parameter_when_cache_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    def _explode(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called in non-TTY mode")

    monkeypatch.setattr(typer, "prompt", _explode)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    with pytest.raises(typer.BadParameter, match="password"):
        _client_factory.make_cloudaz_client(ctx)


def test_explicit_password_bypasses_cache_lookup_and_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured = _capture_cloudaz_kwargs(monkeypatch)

    def _explode_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called when --password is set")

    def _explode_cache_load(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("cache must not be consulted when --password is set")

    monkeypatch.setattr(typer, "prompt", _explode_prompt)
    monkeypatch.setattr(FileTokenCache, "load", _explode_cache_load)

    ctx = _make_ctx(password="explicit", cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] == "explicit"


def test_fresh_access_token_proceeds_without_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _seed_token(
        tmp_path,
        expires_at=10**12,
        refresh_token=None,
        refresh_expires_at=None,
    )
    captured = _capture_cloudaz_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    def _explode_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called for fresh token")

    monkeypatch.setattr(typer, "prompt", _explode_prompt)

    ctx = _make_ctx(password=None, cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] is None
