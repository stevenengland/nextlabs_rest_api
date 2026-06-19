"""Tests for the inline highlighter and semantic renderer."""

from rich.console import Console

from nextlabs_sdk._cli._diff._models import DiffResult, FieldChange


def test_highlight_inline_emphasises_only_changed_word():
    """Test that only changed words are emphasised.

    Given two scalar strings differing by one word,
    when highlighting the change inline,
    then only the changed word carries emphasis; unchanged words are plain.
    """
    from nextlabs_sdk._cli._diff._inline import highlight_inline

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
    from nextlabs_sdk._cli._diff._inline import highlight_inline

    text = "allow read access"
    markup = highlight_inline(text, text)
    assert "[bold yellow]" not in markup


def test_render_semantic_shows_inplace_scalar_change():
    """Test that the renderer shows in-place scalar changes with highlighted words.

    Given a delta with a single scalar description edit,
    when rendering to a captured console,
    then the changed word and the hidden-noise footer are present in-place.
    """
    from nextlabs_sdk._cli._diff._render_semantic import render_semantic

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
    console = Console()
    with console.capture() as capture:
        render_semantic(result, console=console)
    output = capture.get()
    assert "write" in output
    assert "access" in output
    assert "2 noise-only" in output
