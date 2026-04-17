from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import typer

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._account_preferences import AccountPreferences
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
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
