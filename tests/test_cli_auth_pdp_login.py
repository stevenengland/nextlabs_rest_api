from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import httpx
import pytest
from mockito import ANY, mock, when
from strip_ansi import strip_ansi
from typer.testing import CliRunner

from nextlabs_sdk._auth._active_account._active_account_store import (
    ActiveAccountStore,
)
from nextlabs_sdk._auth._token_cache._file_token_cache import FileTokenCache
from nextlabs_sdk._cli import _auth_cmd, _client_factory
from nextlabs_sdk._cli._account_preferences_store import AccountPreferencesStore
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
from nextlabs_sdk._cli._ssl_retry import SslRetryPrompter
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._operators import OperatorService

runner = CliRunner()


class _RecordingPrompter(SslRetryPrompter):
    """Test double that records the ``target_url`` it is handed."""

    def __init__(
        self,
        sink: list[str],
        *,
        isatty: Callable[[], bool],
        confirm: Callable[..., bool],
    ) -> None:
        super().__init__(isatty=isatty, confirm=confirm)
        self._sink = sink

    def run_with_ssl_retry(
        self,
        *,
        attempt: Callable[[CliContext], None],
        cli_ctx: CliContext,
        target_url: str,
    ) -> CliContext:
        self._sink.append(target_url)
        return super().run_with_ssl_retry(
            attempt=attempt,
            cli_ctx=cli_ctx,
            target_url=target_url,
        )


def _mock_cloudaz_client() -> CloudAzClient:
    client = mock(CloudAzClient)
    ops = mock(OperatorService)
    client.operators = ops
    when(ops).list_types().thenReturn([])
    when(client).authenticate().thenReturn(None)
    return cast(CloudAzClient, client)


def _isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTLABS_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)


def _capture_factory(monkeypatch: pytest.MonkeyPatch) -> list[CliContext]:
    captured: list[CliContext] = []

    def _fake(ctx: CliContext) -> CloudAzClient:
        captured.append(ctx)
        return _mock_cloudaz_client()

    monkeypatch.setattr(_client_factory, "make_cloudaz_client", _fake)
    return captured


def test_login_type_cloudaz_keeps_existing_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    captured = _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
            "--type",
            "cloudaz",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured and captured[0].base_url == "https://example.com"


def test_login_without_type_in_non_tty_defaults_to_cloudaz(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
        ],
    )

    assert result.exit_code == 0, result.output


def test_login_type_pdp_reaches_branch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    called: list[bool] = []

    def _fake_pdp(cli_ctx: CliContext) -> None:
        called.append(True)

    monkeypatch.setattr(_auth_cmd, "_login_pdp", _fake_pdp)

    result = runner.invoke(app, ["auth", "login", "--type", "pdp"])

    assert called == [True]
    assert result.exit_code == 0, result.output


def test_login_type_invalid_raises_bad_parameter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://example.com",
            "--username",
            "admin",
            "--password",
            "secret",
            "auth",
            "login",
            "--type",
            "bogus",
        ],
    )

    assert result.exit_code != 0
    assert "type" in result.output.lower()


# ─────────────────────────── Task 5: PDP login ───────────────────────────


class _TokenResp:
    status_code = 200
    text = ""

    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def json(self) -> dict[str, object]:
        return self._body


class _ErrResp:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


def test_login_pdp_pdp_flavor_persists_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )
    when(httpx).post(
        "https://pdp.example/dpc/oauth",
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(resp)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output

    cache = FileTokenCache(path=tmp_path / "tokens.json")
    entry = cache.load("https://pdp.example||ccid|pdp")
    assert entry is not None
    assert entry.access_token == "AT"
    assert entry.client_secret == "S3cret"

    prefs = AccountPreferencesStore(
        path=tmp_path / "account_prefs.json",
    ).load("https://pdp.example||ccid|pdp")
    assert prefs is not None
    assert prefs.pdp_url == "https://pdp.example"
    assert prefs.pdp_auth_source == "pdp"

    active = ActiveAccountStore(path=tmp_path / "active_account.json").load()
    assert active is not None
    assert active.kind == "pdp"
    assert active.base_url == "https://pdp.example"
    assert active.username == ""


def test_login_pdp_cloudaz_flavor_requires_base_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "cc",
            "--client-secret",
            "S",
            "--pdp-auth",
            "cloudaz",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code != 0
    assert "base-url" in result.output.lower()


def test_login_pdp_token_error_surfaces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_ErrResp(status_code=401, text="bad creds"))

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "cc",
            "--client-secret",
            "bad",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    assert (
        "authentication failed" in result.output.lower()
        or "token acquisition" in result.output.lower()
    )


def test_login_pdp_uses_pdp_client_id_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    resp = _TokenResp({"access_token": "AT", "expires_in": 3600})
    captured_data: list[dict[str, str]] = []

    def _fake_post(
        url: str,
        *,
        data: dict[str, str],
        **_kwargs: object,
    ) -> _TokenResp:
        captured_data.append(dict(data))
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "pdp-only-id",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured_data == [
        {
            "grant_type": "client_credentials",
            "client_id": "pdp-only-id",
            "client_secret": "S3cret",
        },
    ]

    entry = FileTokenCache(path=tmp_path / "tokens.json").load(
        "https://pdp.example||pdp-only-id|pdp",
    )
    assert entry is not None
    assert entry.access_token == "AT"


def _isatty_false_for_pdp_login() -> bool:
    return False


def test_login_pdp_rejects_missing_client_id_non_tty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false_for_pdp_login)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code != 0
    assert "pdp-client-id" in result.output.lower()


def test_login_pdp_cloudaz_flavor_uses_client_id_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    resp = _TokenResp({"access_token": "AT", "expires_in": 3600})
    captured_data: list[dict[str, str]] = []

    def _fake_post(
        url: str,
        *,
        data: dict[str, str],
        **_kwargs: object,
    ) -> _TokenResp:
        captured_data.append(dict(data))
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://cloudaz.example",
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "cloudaz-oidc-client",
            "--client-secret",
            "S",
            "--pdp-auth",
            "cloudaz",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured_data == [
        {
            "grant_type": "client_credentials",
            "client_id": "cloudaz-oidc-client",
            "client_secret": "S",
        },
    ]


def test_login_pdp_surfaces_oauth_error_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    body: dict[str, object] = {
        "error": "invalid_client",
        "error_description": "Client authentication failed",
    }
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_TokenResp(body))

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "c",
            "--client-secret",
            "bad",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    normalized = " ".join(strip_ansi(result.output).split())
    assert "invalid_client" in normalized
    assert "Client authentication failed" in normalized


def test_login_pdp_null_error_falls_back_to_body_snippet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    body: dict[str, object] = {"error": None, "detail": "weird-sentinel"}
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_BodyResp(body, '{"error": null, "detail": "weird-sentinel"}'))

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "c",
            "--client-secret",
            "s",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    normalized = " ".join(strip_ansi(result.output).split())
    assert "OAuth error: None" not in normalized
    assert "missing 'access_token'" in normalized
    assert "weird-sentinel" in normalized


class _BodyResp:
    status_code = 200

    def __init__(self, body: dict[str, object], text: str) -> None:
        self._body = body
        self.text = text

    def json(self) -> dict[str, object]:
        return self._body


def test_login_pdp_200_missing_access_token_includes_body_snippet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(
        _BodyResp({"foo": "bar"}, '{"foo": "bar"}'),
    )

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "c",
            "--client-secret",
            "s",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    normalized = " ".join(strip_ansi(result.output).split())
    assert "foo" in normalized
    assert "bar" in normalized


def test_login_pdp_non_200_includes_body_snippet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        ANY,
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_ErrResp(status_code=401, text="invalid client credentials"))

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--pdp-client-id",
            "c",
            "--client-secret",
            "bad",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    normalized = " ".join(strip_ansi(result.output).split())
    assert "401" in normalized
    assert "invalid client credentials" in normalized


# ─────────────────────── Recommended regression tests ──────────────────────


from click.testing import Result as _CliResult


def _invoke_pdp_login(secret: str) -> _CliResult:
    return runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            secret,
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )


def test_pdp_relogin_overwrites_client_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        "https://pdp.example/dpc/oauth",
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(
        _TokenResp({"access_token": "AT", "expires_in": 3600}),
    )

    first = _invoke_pdp_login("OLD")
    assert first.exit_code == 0, first.output
    second = _invoke_pdp_login("NEW")
    assert second.exit_code == 0, second.output

    entry = FileTokenCache(path=tmp_path / "tokens.json").load(
        "https://pdp.example||ccid|pdp",
    )
    assert entry is not None
    assert entry.client_secret == "NEW"


def test_cloudaz_login_still_uses_four_segment_cache_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    _capture_factory(monkeypatch)

    result = runner.invoke(
        app,
        [
            "--base-url",
            "https://cloudaz.example",
            "--username",
            "alice",
            "--password",
            "secret",
            "auth",
            "login",
        ],
    )

    assert result.exit_code == 0, result.output
    active = ActiveAccountStore(path=tmp_path / "active_account.json").load()
    assert active is not None
    assert active.kind == "cloudaz"

    from nextlabs_sdk._cli._account_menu import (
        AccountIdentifier,
        cache_key_for,
    )

    key = cache_key_for(
        AccountIdentifier(
            base_url=active.base_url,
            username=active.username,
            client_id=active.client_id,
            kind=active.kind,
        ),
    )
    assert key.count("|") == 3
    assert key.endswith("|cloudaz")


def test_switching_active_account_between_kinds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_cache(tmp_path, monkeypatch)
    when(httpx).post(
        "https://pdp.example/dpc/oauth",
        data=ANY,
        headers=ANY,
        timeout=ANY,
        verify=ANY,
    ).thenReturn(_TokenResp({"access_token": "AT", "expires_in": 3600}))

    from nextlabs_sdk._auth._token_cache._cached_token import CachedToken

    cache = FileTokenCache(path=tmp_path / "tokens.json")
    cache.save(
        "https://cloudaz.example/cas/oidc/accessToken|alice|cc|cloudaz",
        CachedToken(
            access_token="id",
            refresh_token="rt",
            expires_at=9_999_999_999.0,
            token_type="bearer",
            scope=None,
        ),
    )

    pdp = _invoke_pdp_login("S")
    assert pdp.exit_code == 0, pdp.output

    active_store = ActiveAccountStore(path=tmp_path / "active_account.json")
    active_after_pdp = active_store.load()
    assert active_after_pdp is not None and active_after_pdp.kind == "pdp"

    back = runner.invoke(
        app,
        ["auth", "use", "alice@https://cloudaz.example"],
    )
    assert back.exit_code == 0, back.output
    active_after_back = active_store.load()
    assert active_after_back is not None
    assert active_after_back.kind == "cloudaz"

    forward = runner.invoke(
        app,
        ["auth", "use", "[pdp]@https://pdp.example"],
    )
    assert forward.exit_code == 0, forward.output
    active_after_forward = active_store.load()
    assert active_after_forward is not None
    assert active_after_forward.kind == "pdp"


def _install_pdp_ssl_retry_prompter(
    monkeypatch: pytest.MonkeyPatch,
    *,
    isatty: bool,
    confirm: bool = True,
) -> None:
    from nextlabs_sdk._cli import _pdp_login
    from nextlabs_sdk._cli._ssl_retry import SslRetryPrompter

    def _factory() -> SslRetryPrompter:
        return SslRetryPrompter(
            isatty=lambda: isatty,
            confirm=lambda _text, *, default=False: confirm,
        )

    monkeypatch.setattr(_pdp_login, "_SSL_RETRY_PROMPTER_FACTORY", _factory)


def test_pdp_login_ssl_failure_retries_and_persists_verify_ssl_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ssl

    _isolate_cache(tmp_path, monkeypatch)
    calls_verify: list[object] = []

    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )

    def _fake_post(*_args: object, **kwargs: object) -> object:
        calls_verify.append(kwargs.get("verify"))
        if len(calls_verify) == 1:
            cause = ssl.SSLCertVerificationError("verify failed")
            wrapped = httpx.ConnectError("verify failed")
            wrapped.__cause__ = cause
            raise wrapped
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)
    _install_pdp_ssl_retry_prompter(monkeypatch, isatty=True, confirm=True)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls_verify == [True, False]

    prefs = AccountPreferencesStore(
        path=tmp_path / "account_prefs.json",
    ).load("https://pdp.example||ccid|pdp")
    assert prefs is not None
    assert prefs.verify_ssl is False
    assert prefs.pdp_url == "https://pdp.example"
    assert prefs.pdp_auth_source == "pdp"


def test_pdp_login_non_tty_does_not_prompt_on_ssl_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ssl

    _isolate_cache(tmp_path, monkeypatch)

    def _fake_post(*_args: object, **_kwargs: object) -> object:
        cause = ssl.SSLCertVerificationError("verify failed")
        wrapped = httpx.ConnectError("verify failed")
        wrapped.__cause__ = cause
        raise wrapped

    monkeypatch.setattr(httpx, "post", _fake_post)
    _install_pdp_ssl_retry_prompter(monkeypatch, isatty=False, confirm=True)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 1
    normalized = strip_ansi(result.output)
    assert "Connection error" in normalized or "SSL" in normalized


def test_pdp_login_ssl_retry_does_not_reprompt_for_missing_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inputs supplied interactively once are reused on retry.

    Regression guard for Copilot review on PR #64: if
    ``_attempt_login`` were called twice against the original
    (partially unresolved) ``CliContext``, each helper resolver would
    fire twice — including the interactive ``typer.prompt`` paths.
    """
    import ssl

    from nextlabs_sdk._cli import _pdp_login as _pdp_login_module

    _isolate_cache(tmp_path, monkeypatch)

    pdp_url_calls = [0]
    client_secret_calls = [0]
    original_pdp_url = _pdp_login_module._resolve_pdp_url
    original_client_secret = _pdp_login_module._resolve_client_secret

    def _counting_pdp_url(ctx: CliContext, flavor: PdpAuthSource) -> str:
        if ctx.pdp_url is None:
            pdp_url_calls[0] += 1
            return "https://pdp.example"
        return original_pdp_url(ctx, flavor)

    def _counting_client_secret(ctx: CliContext, flavor: PdpAuthSource) -> str:
        if ctx.client_secret is None:
            client_secret_calls[0] += 1
            return "S3cret"
        return original_client_secret(ctx, flavor)

    monkeypatch.setattr(
        _pdp_login_module,
        "_resolve_pdp_url",
        _counting_pdp_url,
    )
    monkeypatch.setattr(
        _pdp_login_module,
        "_resolve_client_secret",
        _counting_client_secret,
    )

    calls_verify: list[object] = []
    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )

    def _fake_post(*_args: object, **kwargs: object) -> object:
        calls_verify.append(kwargs.get("verify"))
        if len(calls_verify) == 1:
            cause = ssl.SSLCertVerificationError("verify failed")
            wrapped = httpx.ConnectError("verify failed")
            wrapped.__cause__ = cause
            raise wrapped
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)
    _install_pdp_ssl_retry_prompter(monkeypatch, isatty=True, confirm=True)

    result = runner.invoke(
        app,
        [
            "--pdp-client-id",
            "ccid",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls_verify == [True, False]
    assert pdp_url_calls == [1]
    assert client_secret_calls == [1]


def test_pdp_login_ssl_retry_target_url_reflects_resolved_pdp_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The prompt message shows the resolved PDP URL, not an empty string.

    Regression guard for Copilot review on PR #64: previously,
    ``target_url`` was computed from the *unresolved* CliContext, so a
    user prompted for ``--pdp-url`` would see "SSL verification failed
    for ." with an empty URL.
    """
    from nextlabs_sdk._cli import _pdp_login as _pdp_login_module

    _isolate_cache(tmp_path, monkeypatch)

    original_pdp_url = _pdp_login_module._resolve_pdp_url

    def _fake_pdp_url(ctx: CliContext, flavor: PdpAuthSource) -> str:
        if ctx.pdp_url is None:
            return "https://pdp.example"
        return original_pdp_url(ctx, flavor)

    monkeypatch.setattr(
        _pdp_login_module,
        "_resolve_pdp_url",
        _fake_pdp_url,
    )

    observed_target: list[str] = []

    monkeypatch.setattr(
        _pdp_login_module,
        "_SSL_RETRY_PROMPTER_FACTORY",
        lambda: _RecordingPrompter(
            observed_target,
            isatty=lambda: True,
            confirm=lambda _t, *, default=False: True,
        ),
    )

    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )

    def _fake_post(*_args: object, **_kwargs: object) -> object:
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = runner.invoke(
        app,
        [
            "--pdp-client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert observed_target == ["https://pdp.example"]


_PDP_PREFS_KEY = "https://pdp.example||ccid|pdp"


def _seed_pdp_prefs_verify_false(tmp_path: Path) -> AccountPreferencesStore:
    from nextlabs_sdk._cli._account_preferences import AccountPreferences

    store = AccountPreferencesStore(path=tmp_path / "account_prefs.json")
    store.save(
        _PDP_PREFS_KEY,
        AccountPreferences(
            verify_ssl=False,
            pdp_url="https://pdp.example",
            pdp_auth_source="pdp",
        ),
    )
    return store


def test_pdp_login_without_flag_preserves_persisted_verify_ssl_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Silent PDP re-login must keep a persisted ``verify_ssl=False``.

    Regresses the symmetric CloudAz bug: the PDP login derived the
    ``verify_ssl`` it used for the token POST (and the pref it then
    wrote) solely from the CLI flag, so a re-login without
    ``--no-verify`` would attempt the request with TLS verification
    on and then persist ``True`` even if the prior preference was
    ``False``.
    """
    _isolate_cache(tmp_path, monkeypatch)
    store = _seed_pdp_prefs_verify_false(tmp_path)
    calls_verify: list[object] = []
    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )

    def _fake_post(*_args: object, **kwargs: object) -> object:
        calls_verify.append(kwargs.get("verify"))
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = runner.invoke(
        app,
        [
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls_verify == [False]
    prefs = store.load(_PDP_PREFS_KEY)
    assert prefs is not None
    assert prefs.verify_ssl is False


def test_pdp_login_with_explicit_verify_flag_overrides_persisted_false(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit ``--verify`` still wins over a persisted ``False``."""
    _isolate_cache(tmp_path, monkeypatch)
    store = _seed_pdp_prefs_verify_false(tmp_path)
    calls_verify: list[object] = []
    resp = _TokenResp(
        {"access_token": "AT", "expires_in": 3600, "token_type": "bearer"},
    )

    def _fake_post(*_args: object, **kwargs: object) -> object:
        calls_verify.append(kwargs.get("verify"))
        return resp

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = runner.invoke(
        app,
        [
            "--verify",
            "--pdp-url",
            "https://pdp.example",
            "--client-id",
            "ccid",
            "--client-secret",
            "S3cret",
            "--pdp-auth",
            "pdp",
            "auth",
            "login",
            "--type",
            "pdp",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls_verify == [True]
    prefs = store.load(_PDP_PREFS_KEY)
    assert prefs is not None
    assert prefs.verify_ssl is True
