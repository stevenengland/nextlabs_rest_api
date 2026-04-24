"""Build an ``ActivityLogQuery`` from an optional file and inline flags.

Supports layered configuration: values from the ``--query`` JSON file
are overlaid by any inline flags the user explicitly passed. When no
file is given, defaults derived from a known-good live payload fill in
optional fields so users can run ``search`` with no flags at all.
"""

from __future__ import annotations

from pathlib import Path

from nextlabs_sdk._cli._payload_loader import load_payload
from nextlabs_sdk._cli._time_parser import now_epoch_ms, parse_time
from nextlabs_sdk._cloudaz._activity_log_query_models import ActivityLogQuery
from nextlabs_sdk.exceptions import NextLabsError

_DEFAULT_POLICY_DECISION = "AD"
_DEFAULT_SORT_BY = "ROW_ID"
_DEFAULT_SORT_ORDER = "descending"
_DEFAULT_FIELD_NAME = ""
_DEFAULT_FIELD_VALUE = ""
_DEFAULT_WINDOW_MS = 24 * 60 * 60 * 1000
_FROM_DATE_KEY = "from_date"
_TO_DATE_KEY = "to_date"


def build_activity_log_query(  # noqa: WPS211
    query_path: Path | None,
    *,
    policy_decision: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    field_name: str | None = None,
    field_value: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    header: list[str] | None = None,
    page: int | None = None,
    size: int | None = None,
    default_header: list[str] | None = None,
) -> ActivityLogQuery:
    """Compose an ``ActivityLogQuery`` from an optional file and flags.

    Args:
        query_path: Optional path to a JSON payload matching
            ``ActivityLogQuery``. When given, acts as the base config.
        policy_decision: Overlay for ``policyDecision``.
        sort_by: Overlay for ``sortBy``.
        sort_order: Overlay for ``sortOrder``.
        field_name: Overlay for ``fieldName``.
        field_value: Overlay for ``fieldValue``.
        from_date: Overlay for ``fromDate``; accepts formats handled by
            :func:`parse_time` (epoch ms, ISO 8601, relative offset).
        to_date: Overlay for ``toDate``; same formats as ``from_date``.
        header: Overlay for the ``header`` list (full replacement).
        page: Overlay for ``page``.
        size: Overlay for ``size``.
        default_header: Fallback ``header`` list applied only when
            ``query_path`` is ``None`` and ``header`` is ``None``. Lets
            the caller supply the CLI's render columns so picky servers
            accept the payload and wide output never blanks.

    Returns:
        A validated ``ActivityLogQuery``.

    Raises:
        NextLabsError: If the merged payload fails validation, or if a
            date string cannot be parsed.
        typer.Exit: If the file is missing, unreadable, or not JSON
            (propagated from :func:`load_payload`).
    """
    inline_mode = query_path is None

    base: dict[str, object] = dict(load_payload(query_path)) if query_path else {}

    overrides = _collect_overrides(
        policy_decision=policy_decision,
        sort_by=sort_by,
        sort_order=sort_order,
        field_name=field_name,
        field_value=field_value,
        from_date=from_date,
        to_date=to_date,
        header=header,
        page=page,
        size=size,
    )
    base.update(overrides)

    if inline_mode:
        _apply_inline_defaults(base, default_header=default_header)

    try:
        return ActivityLogQuery.model_validate(base)
    except ValueError as exc:
        location = f" in {query_path}" if query_path else ""
        raise NextLabsError(
            f"Invalid activity log query{location}: {exc}",
        ) from None


def _apply_inline_defaults(
    base: dict[str, object], *, default_header: list[str] | None
) -> None:
    base.setdefault("policy_decision", _DEFAULT_POLICY_DECISION)
    base.setdefault("sort_by", _DEFAULT_SORT_BY)
    base.setdefault("sort_order", _DEFAULT_SORT_ORDER)
    base.setdefault("field_name", _DEFAULT_FIELD_NAME)
    base.setdefault("field_value", _DEFAULT_FIELD_VALUE)
    _apply_date_window_defaults(base)
    if default_header is not None and "header" not in base:
        base["header"] = list(default_header)


def _apply_date_window_defaults(base: dict[str, object]) -> None:
    has_from = _FROM_DATE_KEY in base
    has_to = _TO_DATE_KEY in base
    if has_from and has_to:
        return
    now = now_epoch_ms()
    if not has_from and not has_to:
        base[_FROM_DATE_KEY] = now - _DEFAULT_WINDOW_MS
        base[_TO_DATE_KEY] = now
    elif has_from and not has_to:
        base[_TO_DATE_KEY] = now
    else:
        to_date = base[_TO_DATE_KEY]
        assert isinstance(to_date, int)
        base[_FROM_DATE_KEY] = to_date - _DEFAULT_WINDOW_MS


def _collect_overrides(  # noqa: WPS211
    *,
    policy_decision: str | None,
    sort_by: str | None,
    sort_order: str | None,
    field_name: str | None,
    field_value: str | None,
    from_date: str | None,
    to_date: str | None,
    header: list[str] | None,
    page: int | None,
    size: int | None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if policy_decision is not None:
        overrides["policy_decision"] = policy_decision
    if sort_by is not None:
        overrides["sort_by"] = sort_by
    if sort_order is not None:
        overrides["sort_order"] = sort_order
    if field_name is not None:
        overrides["field_name"] = field_name
    if field_value is not None:
        overrides["field_value"] = field_value
    if from_date is not None:
        overrides["from_date"] = _parse_date(from_date, "--from-date")
    if to_date is not None:
        overrides["to_date"] = _parse_date(to_date, "--to-date")
    if header is not None:
        overrides["header"] = header
    if page is not None:
        overrides["page"] = page
    if size is not None:
        overrides["size"] = size
    return overrides


def _parse_date(raw: str, flag: str) -> int:
    try:
        return parse_time(raw)
    except ValueError as exc:
        raise NextLabsError(f"Invalid {flag} value: {exc}") from None
