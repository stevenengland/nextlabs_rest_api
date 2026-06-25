from __future__ import annotations

import io
from typing import Any

from rich.console import Console
from strip_ansi import strip_ansi

from nextlabs_sdk._cli._diff._engine import diff_payloads
from nextlabs_sdk._cli._diff._models import DiffHeader
from nextlabs_sdk._cli._diff._render_unified import UnifiedDiffInput, render_unified

_HEADER = DiffHeader(policy_name="P", policy_id=82, from_rev=2, to_rev=3)


def _render(old: dict[str, Any], new: dict[str, Any], **kwargs: Any) -> str:
    buffer = io.StringIO()
    console = Console(file=buffer, force_terminal=False, width=200)
    diff_result = diff_payloads(old, new, show_all=kwargs.get("show_all", False))
    render_unified(
        UnifiedDiffInput(old=old, new=new, header=_HEADER, diff_result=diff_result),
        console=console,
        **kwargs,
    )
    return strip_ansi(buffer.getvalue())


def _body_change_lines(output: str) -> list[str]:
    return [
        line
        for line in output.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]


def test_reordered_array_produces_no_diff_lines() -> None:
    """Given two payloads whose only difference is the order of an array's
    elements, when rendering the unified diff, then no change lines are
    emitted because both sides are canonicalised first."""
    old = {"name": "P", "items": [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]}
    new = {"name": "P", "items": [{"id": 2, "v": "b"}, {"id": 1, "v": "a"}]}
    output = _render(old, new)
    assert _body_change_lines(output) == []


def test_noise_field_change_produces_no_diff_lines() -> None:
    """Given two payloads differing only in a deployment-noise field, when
    rendering the unified diff, then no change lines are emitted because the
    noise blacklist is stripped during canonicalisation."""
    old = {"name": "P", "deploymentTime": 100}
    new = {"name": "P", "deploymentTime": 200}
    output = _render(old, new)
    assert _body_change_lines(output) == []


def test_real_change_renders_git_style_unified_diff() -> None:
    """Given two payloads with a genuinely changed scalar, when rendering the
    unified diff, then it emits a git-style hunk with removed and added
    lines carrying the old and new values."""
    old = {"name": "P", "description": "allow read access"}
    new = {"name": "P", "description": "allow write access"}
    output = _render(old, new)
    assert "@@" in output
    changes = _body_change_lines(output)
    assert any(line.startswith("-") and "read" in line for line in changes)
    assert any(line.startswith("+") and "write" in line for line in changes)


def test_show_all_reveals_noise_field_in_unified_diff() -> None:
    """Given two payloads differing only in a noise field, when rendering the
    unified diff with show_all, then the otherwise-stripped noise field
    surfaces as a change line."""
    old = {"name": "P", "deploymentTime": 100}
    new = {"name": "P", "deploymentTime": 200}
    output = _render(old, new, show_all=True)
    assert "deploymentTime" in output
    assert _body_change_lines(output) != []


def test_header_renders_policy_row_and_derives_revision_labels() -> None:
    """Given a DiffHeader and two differing payloads, when rendering the unified
    diff, then a single 'Policy: <name> (id=<id>)' row precedes the diff and the
    git --- / +++ labels are derived from the header's revision numbers."""
    old = {"name": "P", "description": "allow read access"}
    new = {"name": "P", "description": "allow write access"}
    output = _render(old, new)
    lines = output.splitlines()
    assert lines[0] == "Policy: P (id=82)"
    assert lines[1] == ""
    assert "--- revision 2" in output
    assert "+++ revision 3" in output


def test_header_renders_when_revisions_are_identical() -> None:
    """Given two identical payloads, when rendering the unified diff, then the
    'Policy:' row is still emitted where the renderer previously printed
    nothing."""
    payload = {"name": "P", "description": "allow read access"}
    output = _render(dict(payload), dict(payload))
    assert output.splitlines()[0] == "Policy: P (id=82)"
    assert _body_change_lines(output) == []
