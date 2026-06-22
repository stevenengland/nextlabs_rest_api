"""Word-level inline highlighter for scalar string diffs."""

from __future__ import annotations

import difflib

_BOLD_YELLOW_OPEN = "[bold yellow]"
_BOLD_YELLOW_CLOSE = "[/bold yellow]"


def _wrap(words: list[str]) -> str:
    return " ".join(f"{_BOLD_YELLOW_OPEN}{word}{_BOLD_YELLOW_CLOSE}" for word in words)


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
            parts.extend(
                f"{_BOLD_YELLOW_OPEN}{word}{_BOLD_YELLOW_CLOSE}" for word in segment
            )
    return " ".join(parts)


def highlight_pair(old: str, new: str) -> tuple[str, str]:
    """Return ``(old_markup, new_markup)`` with changed words emphasised on each side.

    Args:
        old: The previous scalar string value.
        new: The updated scalar string value.

    Returns:
        A tuple where ``old_markup`` wraps removed/replaced words in
        ``[bold yellow]...[/bold yellow]`` and ``new_markup`` wraps
        inserted/replaced words likewise; unchanged words stay plain on both.
    """
    old_words = old.split()
    new_words = new.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
    old_parts: list[str] = []
    new_parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            old_parts.extend(old_words[i1:i2])
            new_parts.extend(new_words[j1:j2])
        else:
            if i1 < i2:
                old_parts.append(_wrap(old_words[i1:i2]))
            if j1 < j2:
                new_parts.append(_wrap(new_words[j1:j2]))
    return " ".join(old_parts), " ".join(new_parts)
