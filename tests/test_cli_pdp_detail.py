from __future__ import annotations

import io

from rich.console import Console

from nextlabs_sdk._cli import _pdp_cmd
from nextlabs_sdk._cli._detail_renderers import render_detail
from nextlabs_sdk._pdp import (
    ActionPermission,
    Decision,
    EvalResponse,
    EvalResult,
    Obligation,
    ObligationAttribute,
    PermissionsResponse,
    PolicyRef,
    Status,
)


def _console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, force_terminal=False, width=120, color_system=None), buf


def test_pdp_eval_detail_renderer_registered() -> None:
    assert _pdp_cmd.pdp_app is not None
    response = EvalResponse(
        eval_results=[
            EvalResult(
                decision=Decision.PERMIT,
                status=Status(code="urn:oasis:names:tc:xacml:1.0:status:ok"),
                obligations=[
                    Obligation(
                        id="log-obligation",
                        attributes=[
                            ObligationAttribute(id="log-level", attr_value="info"),
                        ],
                    ),
                ],
                policy_refs=[PolicyRef(id="AllowAll", version="1.0")],
            ),
        ],
    )
    console, buf = _console()
    render_detail(response, console=console)
    output = buf.getvalue()
    assert "Decision:" in output
    assert "Permit" in output
    assert "Status:" in output
    assert "Obligations" in output
    assert "log-obligation" in output
    assert "log-level" in output
    assert "Matched Policies" in output
    assert "AllowAll" in output


def test_pdp_permissions_detail_renderer_registered() -> None:
    assert _pdp_cmd.pdp_app is not None
    response = PermissionsResponse(
        allowed=[ActionPermission(name="VIEW")],
        denied=[ActionPermission(name="DELETE")],
        dont_care=[],
    )
    console, buf = _console()
    render_detail(response, console=console)
    output = buf.getvalue()
    assert "Allowed" in output
    assert "VIEW" in output
    assert "Denied" in output
    assert "DELETE" in output
