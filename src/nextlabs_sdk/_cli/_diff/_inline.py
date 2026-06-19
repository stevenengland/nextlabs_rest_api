"""Word-level inline highlighter for scalar string diffs."""

from __future__ import annotations

import difflib


def highlight_inline(old: str, new: str) -> str:
    """Return *new* with only inserted/replaced words wrapped in Rich emphasis.

    Args:
        old: The previous scalar string value.
        new: The updated scalar string value.

    Returns:
        The new string with changed words wrapped in ``[bold yellow]...[/bold yellow]``.
    """
    old_words = old.split()
    new_words = new.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
    parts: list[str] = []
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        segment = new_words[j1:j2]
        if tag == "equal":
            parts.extend(segment)
        else:
            parts.extend(f"[bold yellow]{word}[/bold yellow]" for word in segment)
    return " ".join(parts)
