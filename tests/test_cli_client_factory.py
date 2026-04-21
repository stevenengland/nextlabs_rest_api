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
from nextlabs_sdk._cli._cache_key import cache_key_for
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
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
    pdp_url: str | None = "https://pdp.example.com",
    pdp_auth: PdpAuthSource | None = None,
    pdp_client_id: str | None = None,
) -> CliContext:
    return CliContext(
        base_url=base_url,
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
        pdp_url=pdp_url,
        output_format=OutputFormat.TABLE,
        verify=verify,
        timeout=30.0,
        cache_dir=cache_dir,
        pdp_auth=pdp_auth,
        pdp_client_id=pdp_client_id,
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
            {"client_secret": None},
            "client-secret",
            id="pdp-client-secret",
        ),
        pytest.param(
            _client_factory.make_pdp_client,
            {"pdp_url": None},
            "pdp-url",
            id="pdp-pdp-url",
        ),
        pytest.param(
            _client_factory.make_pdp_client,
            {"base_url": None, "pdp_url": None},
            "pdp-url",
            id="pdp-pdp-url-default-flavor-pdp",
        ),
        pytest.param(
            _client_factory.make_pdp_client,
            {"base_url": None, "pdp_auth": PdpAuthSource.CLOUDAZ},
            "base-url",
            id="pdp-cloudaz-flavor-needs-base-url",
        ),
    ],
)
def test_factory_raises_when_required_field_missing(
    factory, kwargs, match, monkeypatch
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)
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
_CACHE_KEY = cache_key_for(_ACCOUNT)


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


def test_empty_password_is_treated_as_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An empty --password / NEXTLABS_PASSWORD must not bypass the gate."""
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    def _explode_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("typer.prompt must not be called in non-TTY mode")

    monkeypatch.setattr(typer, "prompt", _explode_prompt)

    ctx = _make_ctx(password="", cache_dir=str(tmp_path))
    with pytest.raises(typer.BadParameter, match="password"):
        _client_factory.make_cloudaz_client(ctx)


def test_empty_password_falls_back_to_cached_refresh_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Empty password must allow refresh-token fallback rather than bypassing."""
    _seed_token(
        tmp_path,
        expires_at=0,
        refresh_token="rt",
        refresh_expires_at=10**12,
    )
    captured = _capture_cloudaz_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    ctx = _make_ctx(password="", cache_dir=str(tmp_path))
    _client_factory.make_cloudaz_client(ctx)

    assert captured["password"] is None


# ─── PDP auth flavor (--pdp-auth) ──────────────────────────────────────────


def _capture_pdp_kwargs(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def _capture(*_args: object, **kwargs: object) -> PdpClient:
        captured.update(kwargs)
        return cast(PdpClient, object())

    monkeypatch.setattr(_client_factory, "PdpClient", _capture)
    return captured


def test_pdp_default_flavor_is_cloudaz_when_base_url_set(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = _capture_pdp_kwargs(monkeypatch)
    _client_factory.make_pdp_client(_make_ctx())
    assert captured["base_url"] == "https://pdp.example.com"
    assert captured["auth_base_url"] == "https://example.com"


def test_pdp_default_flavor_is_pdp_when_base_url_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = _capture_pdp_kwargs(monkeypatch)
    _client_factory.make_pdp_client(_make_ctx(base_url=None))
    assert captured["base_url"] == "https://pdp.example.com"
    assert captured["auth_base_url"] is None


def test_pdp_explicit_flavor_pdp_overrides_default(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = _capture_pdp_kwargs(monkeypatch)
    _client_factory.make_pdp_client(_make_ctx(pdp_auth=PdpAuthSource.PDP))
    assert captured["auth_base_url"] is None


def test_pdp_explicit_flavor_cloudaz_requires_base_url(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)
    with pytest.raises(typer.BadParameter, match="/cas/token"):
        _client_factory.make_pdp_client(
            _make_ctx(base_url=None, pdp_auth=PdpAuthSource.CLOUDAZ),
        )


def test_pdp_flavor_pdp_missing_pdp_url_mentions_dpc_oauth(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)
    with pytest.raises(typer.BadParameter, match="/dpc/oauth"):
        _client_factory.make_pdp_client(
            _make_ctx(base_url=None, pdp_url=None),
        )


def test_pdp_flavor_cloudaz_missing_client_secret_mentions_cas_token(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)
    with pytest.raises(typer.BadParameter, match="/cas/token"):
        _client_factory.make_pdp_client(_make_ctx(client_secret=None))


def test_pdp_flavor_pdp_missing_client_secret_mentions_dpc_oauth(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)
    with pytest.raises(typer.BadParameter, match="/dpc/oauth"):
        _client_factory.make_pdp_client(
            _make_ctx(base_url=None, client_secret=None),
        )


def test_pdp_prompts_for_pdp_url_in_tty(monkeypatch: pytest.MonkeyPatch):
    captured = _capture_pdp_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)
    prompts: list[str] = []

    def _fake_prompt(text: str, **_: object) -> str:
        prompts.append(text)
        return "https://prompted-pdp.example.com"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)

    _client_factory.make_pdp_client(_make_ctx(pdp_url=None))

    assert captured["base_url"] == "https://prompted-pdp.example.com"
    assert any("PDP" in p for p in prompts)


def test_pdp_prompts_for_base_url_in_tty_when_cloudaz_flavor(
    monkeypatch: pytest.MonkeyPatch,
):
    captured = _capture_pdp_kwargs(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)
    prompts: list[str] = []

    def _fake_prompt(text: str, **_: object) -> str:
        prompts.append(text)
        return "https://prompted-cloudaz.example.com"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)

    _client_factory.make_pdp_client(
        _make_ctx(base_url=None, pdp_auth=PdpAuthSource.CLOUDAZ),
    )

    assert captured["auth_base_url"] == "https://prompted-cloudaz.example.com"
    assert any("CloudAz" in p for p in prompts)


def test_pdp_explicit_flavor_pdp_reaches_factory_via_cli(
    monkeypatch: pytest.MonkeyPatch,
):
    """--pdp-auth pdp propagates into CliContext and make_pdp_client."""
    captured = _capture_pdp_kwargs(monkeypatch)
    ctx = _make_ctx(pdp_auth=PdpAuthSource.PDP)
    _client_factory.make_pdp_client(ctx)
    # With --pdp-auth pdp, base_url is ignored even when set.
    assert captured["auth_base_url"] is None
    assert captured["base_url"] == "https://pdp.example.com"


# ─── Cached PDP credentials (#58 Task 6) ───────────────────────────────────


def _seed_active_pdp(
    tmp_path: Path,
    *,
    base_url: str = "https://pdp.example",
    pdp_url: str = "https://pdp.example",
    flavor: str = "pdp",
    client_secret: str = "CachedSecret",
) -> None:
    from nextlabs_sdk._auth._active_account._active_account import ActiveAccount
    from nextlabs_sdk._auth._active_account._active_account_store import (
        ActiveAccountStore,
    )

    ActiveAccountStore(path=tmp_path / "active_account.json").save(
        ActiveAccount(
            base_url=base_url,
            username="",
            client_id="c",
            kind="pdp",
        ),
    )
    kind_key_base = base_url
    if flavor == "cloudaz":
        kind_key_base = base_url  # keep raw for 4-seg format
    key = f"{kind_key_base}||c|pdp"
    FileTokenCache(path=tmp_path / "tokens.json").save(
        key,
        CachedToken(
            access_token="AT",
            refresh_token=None,
            expires_at=9_999_999_999.0,
            token_type="bearer",
            scope=None,
            client_secret=client_secret,
        ),
    )
    AccountPreferencesStore(path=tmp_path / "account_prefs.json").save(
        key,
        AccountPreferences(
            verify_ssl=True,
            pdp_url=pdp_url,
            pdp_auth_source=flavor,
        ),
    )


def test_make_pdp_client_uses_cached_credentials_when_active_is_pdp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_active_pdp(tmp_path)
    captured = _capture_pdp_kwargs(monkeypatch)
    ctx = _make_ctx(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret=None,
        pdp_url=None,
        cache_dir=str(tmp_path),
    )

    _client_factory.make_pdp_client(ctx)

    assert captured["client_secret"] == "CachedSecret"
    assert captured["base_url"] == "https://pdp.example"
    assert captured["auth_base_url"] is None


def test_make_pdp_client_cli_flag_overrides_cached_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_active_pdp(tmp_path)
    captured = _capture_pdp_kwargs(monkeypatch)
    ctx = _make_ctx(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret="Override",
        pdp_url=None,
        cache_dir=str(tmp_path),
    )

    _client_factory.make_pdp_client(ctx)

    assert captured["client_secret"] == "Override"


def test_make_pdp_client_cloudaz_flavor_from_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_active_pdp(
        tmp_path,
        base_url="https://cloudaz.example",
        pdp_url="https://pdp.example",
        flavor="cloudaz",
    )
    captured = _capture_pdp_kwargs(monkeypatch)
    ctx = _make_ctx(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret=None,
        pdp_url=None,
        cache_dir=str(tmp_path),
    )

    _client_factory.make_pdp_client(ctx)

    assert captured["base_url"] == "https://pdp.example"
    assert captured["auth_base_url"] == "https://cloudaz.example"


def test_make_cloudaz_client_rejects_active_pdp_account(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Active PDP account must not bleed into CloudAz clients (#59 review)."""
    _seed_active_pdp(tmp_path)
    ctx = _make_ctx(
        base_url=None,
        username=None,
        password=None,
        client_id="c",
        client_secret=None,
        pdp_url=None,
        cache_dir=str(tmp_path),
    )
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    with pytest.raises(typer.BadParameter, match="PDP account"):
        _client_factory.make_cloudaz_client(ctx)


# ─── PDP client-id resolver integration (#61) ─────────────────────────────


def test_make_pdp_client_uses_pdp_client_id_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_pdp_kwargs(monkeypatch)

    _client_factory.make_pdp_client(
        _make_ctx(pdp_client_id="pdp-only-id"),
    )

    assert captured["client_id"] == "pdp-only-id"


def test_make_pdp_client_flag_overrides_active_account_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_active_pdp(tmp_path)
    captured = _capture_pdp_kwargs(monkeypatch)
    ctx = _make_ctx(
        base_url=None,
        username=None,
        client_secret=None,
        cache_dir=str(tmp_path),
        pdp_client_id="override-id",
    )

    _client_factory.make_pdp_client(ctx)

    assert captured["client_id"] == "override-id"


def test_make_pdp_client_pdp_flavor_missing_client_id_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    with pytest.raises(typer.BadParameter, match="pdp-client-id"):
        _client_factory.make_pdp_client(
            _make_ctx(
                base_url=None,
                pdp_auth=PdpAuthSource.PDP,
                client_id="ControlCenterOIDCClient",
            ),
        )
