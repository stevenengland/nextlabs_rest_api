"""Tests for the inline highlighter and semantic renderer."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from nextlabs_sdk._cli._diff._identity import TagSummary
from nextlabs_sdk._cli._diff._inline import highlight_inline, highlight_pair
from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange
from nextlabs_sdk._cli._diff._render_semantic import render_semantic


def test_highlight_inline_emphasises_only_changed_word():
    """Test that only changed words are emphasised.

    Given two scalar strings differing by one word,
    when highlighting the change inline,
    then only the changed word carries emphasis; unchanged words are plain.
    """
    old = "allow read access"
    new = "allow write access"
    markup = highlight_inline(old, new)
    assert "[bold yellow]write[/bold yellow]" in markup
    assert "allow" in markup
    assert "[bold yellow]allow[/bold yellow]" not in markup


def test_highlight_inline_unchanged_string_has_no_emphasis():
    """Test that identical strings produce no emphasis markup.

    Given identical strings,
    when highlighting,
    then no emphasis markup is added.
    """
    text = "allow read access"
    markup = highlight_inline(text, text)
    assert "[bold yellow]" not in markup


def test_highlight_pair_emphasises_removed_on_old_and_added_on_new():
    """Test removed words emphasised on the old line, added on the new.

    Given two multi-word strings differing by one word,
    when building the dual-side highlight,
    then the old markup emphasises the removed word and the new markup the added word,
    while shared words stay plain on both sides.
    """
    # given
    old = "allow read access"
    new = "allow write access"
    # when
    old_markup, new_markup = highlight_pair(old, new)
    # then
    assert "[bold yellow]read[/bold yellow]" in old_markup
    assert "[bold yellow]write[/bold yellow]" in new_markup
    assert "[bold yellow]allow[/bold yellow]" not in old_markup
    assert "[bold yellow]access[/bold yellow]" not in new_markup


def test_highlight_pair_identical_strings_have_no_emphasis():
    """Test that identical strings produce no emphasis on either side.

    Given identical strings,
    when building the dual-side highlight,
    then neither side carries emphasis markup.
    """
    # given
    text = "allow read access"
    # when
    old_markup, new_markup = highlight_pair(text, text)
    # then
    assert "[bold yellow]" not in old_markup
    assert "[bold yellow]" not in new_markup


def test_render_semantic_shows_inplace_scalar_change():
    """Test that the renderer shows in-place scalar changes with highlighted words.

    Given a delta with a single scalar description edit,
    when rendering to a captured console,
    then the changed word and the hidden-noise footer are present in-place.
    """
    result = DiffResult(
        changes=(
            FieldChange(
                path=("description",),
                kind="change",
                old="allow read access",
                new="allow write access",
            ),
        ),
        hidden_noise_count=2,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    assert "write" in output
    assert "access" in output
    assert "2 noise-only" in output


def test_render_semantic_scalar_change_shows_old_and_new_lines():
    """Test that a scalar change renders both the old and new value.

    Given a delta with a single scalar effectType change allow -> deny,
    when rendering to a captured console,
    then both the old value on a '-' line and the new value on a '+' line appear.
    """
    # given
    result = DiffResult(
        changes=(
            FieldChange(path=("effectType",), kind="change", old="ALLOW", new="DENY"),
        ),
        hidden_noise_count=0,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    # when
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    # then
    assert "- ALLOW" in output
    assert "+ DENY" in output


def test_render_semantic_empty_and_none_use_placeholders():
    """Test that cleared values render as (empty) / (none) placeholders.

    Given a delta clearing description to '' and obligationName to None,
    when rendering to a captured console,
    then the new '+' lines show '(empty)' and '(none)' while old values remain visible.
    """
    # given
    result = DiffResult(
        changes=(
            FieldChange(path=("description",), kind="change", old="text", new=""),
            FieldChange(path=("obligationName",), kind="change", old="OBL", new=None),
        ),
        hidden_noise_count=0,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    # when
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    # then
    assert "(empty)" in output
    assert "(none)" in output
    assert "text" in output
    assert "OBL" in output


def test_render_semantic_shows_tag_glyph_lines():
    """Test that added and removed tags render as 'key (LABEL)' glyph lines.

    Given a delta adding one tag and removing another,
    when rendering to a captured console,
    then a '+' line shows the added tag and a '-' line the removed tag, both as 'key (LABEL)'.
    """
    # given
    result = DiffResult(
        changes=(
            FieldChange(
                path=("tags",),
                kind="add",
                old=None,
                new=TagSummary(key="adr6", label="ADR6"),
            ),
            FieldChange(
                path=("tags",),
                kind="remove",
                old=TagSummary(key="old1", label="OLD1"),
                new=None,
            ),
        ),
        hidden_noise_count=0,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    # when
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    # then
    assert "+ adr6 (ADR6)" in output
    assert "- old1 (OLD1)" in output


def test_render_semantic_nests_inplace_tag_field_change():
    """Test that an in-place tag field change nests a two-line scalar diff.

    Given a delta with a scalar change under a tag's path,
    when rendering,
    then both the old and new field values appear on '-'/'+' lines.
    """
    # given
    result = DiffResult(
        changes=(
            FieldChange(
                path=("tags", "adr6 (ADR6)", "status"),
                kind="change",
                old="ON",
                new="OFF",
            ),
        ),
        hidden_noise_count=0,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    # when
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    # then
    assert "- ON" in output
    assert "+ OFF" in output


def test_render_semantic_add_remove_stay_single_line():
    """Test that add and remove scalar kinds render on a single line.

    Given a delta with one added scalar and one removed scalar,
    when rendering to a captured console,
    then each renders as a single 'field: value' line (no separate old/new lines).
    """
    # given
    result = DiffResult(
        changes=(
            FieldChange(path=("addedField",), kind="add", old=None, new="hello"),
            FieldChange(path=("goneField",), kind="remove", old="bye", new=None),
        ),
        hidden_noise_count=0,
    )
    console = Console(
        file=StringIO(), force_terminal=False, width=120, color_system=None
    )
    # when
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    # then
    assert "+ addedField: hello" in output
    assert "- goneField: bye" in output
