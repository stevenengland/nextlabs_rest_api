from __future__ import annotations

import pytest
import typer

from nextlabs_sdk._cli._context import CliContext
from nextlabs_sdk._cli._output_format import OutputFormat
from nextlabs_sdk._cli._pdp_auth_source import PdpAuthSource
from nextlabs_sdk._cli._pdp_client_id import resolve_pdp_client_id


def _ctx(
    *,
    client_id: str = "ControlCenterOIDCClient",
    pdp_client_id: str | None = None,
) -> CliContext:
    return CliContext(
        base_url=None,
        username=None,
        password=None,
        client_id=client_id,
        client_secret=None,
        pdp_url=None,
        output_format=OutputFormat.TABLE,
        verify=None,
        timeout=30.0,
        pdp_client_id=pdp_client_id,
    )


def _isatty_false() -> bool:
    return False


def _isatty_true() -> bool:
    return True


def test_resolve_returns_pdp_client_id_when_set() -> None:
    ctx = _ctx(pdp_client_id="my-pdp-client")

    result = resolve_pdp_client_id(ctx, PdpAuthSource.PDP)

    assert result == "my-pdp-client"


def test_resolve_pdp_flavor_falls_back_to_explicit_client_id() -> None:
    ctx = _ctx(client_id="foo")

    result = resolve_pdp_client_id(ctx, PdpAuthSource.PDP)

    assert result == "foo"


def test_resolve_pdp_flavor_rejects_cloudaz_default_when_non_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _ctx()
    monkeypatch.setattr("sys.stdin.isatty", _isatty_false)

    with pytest.raises(typer.BadParameter, match="pdp-client-id"):
        resolve_pdp_client_id(ctx, PdpAuthSource.PDP)


def test_resolve_pdp_flavor_prompts_on_tty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _ctx()
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)
    prompts: list[str] = []

    def _fake_prompt(text: str, **_: object) -> str:
        prompts.append(text)
        return "prompted-id"

    monkeypatch.setattr(typer, "prompt", _fake_prompt)

    result = resolve_pdp_client_id(ctx, PdpAuthSource.PDP)

    assert result == "prompted-id"
    assert prompts and "client" in prompts[0].lower()


def test_resolve_cloudaz_flavor_falls_back_to_client_id_without_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _ctx()
    monkeypatch.setattr("sys.stdin.isatty", _isatty_true)

    def _fail_prompt(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("CloudAz flavor must not prompt")

    monkeypatch.setattr(typer, "prompt", _fail_prompt)

    result = resolve_pdp_client_id(ctx, PdpAuthSource.CLOUDAZ)

    assert result == "ControlCenterOIDCClient"


def test_resolve_cloudaz_flavor_pdp_flag_overrides_client_id() -> None:
    ctx = _ctx(client_id="foo", pdp_client_id="bar")

    result = resolve_pdp_client_id(ctx, PdpAuthSource.CLOUDAZ)

    assert result == "bar"
