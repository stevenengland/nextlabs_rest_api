"""Search-criteria assembly for the ``policies search`` command."""

from __future__ import annotations

import json
from pathlib import Path

from nextlabs_sdk._cloudaz._search import SearchCriteria, SortOrder
from nextlabs_sdk._cloudaz._search.field_expr import parse_field_expr
from nextlabs_sdk._cloudaz._search.where import transpile_where
from nextlabs_sdk.exceptions import SearchExpressionError

_UTF8 = "utf-8"
_EXPRESSION_FLAGS = ("--status", "--effect", "--text", "--tag", "--field", "--where")
_DEFAULT_PAGE_NO = 0
_DEFAULT_PAGE_SIZE = 20


def build_search_criteria(  # noqa: WPS211
    *,
    status: str | None,
    effect: str | None,
    text: str | None,
    tag: str | None,
    field: list[str] | None,
    where: str | None,
    criteria_file: Path | None,
    sort: list[str] | None,
    page_no: int | None,
    page_size: int | None,
) -> SearchCriteria:
    """Build the SearchCriteria for a ``policies search`` invocation.

    Args:
        status: Shorthand status filter.
        effect: Shorthand effect-type filter.
        text: Shorthand text filter.
        tag: Shorthand tag filter.
        field: Repeatable ``NAME[:TYPE]=VALUE`` field expressions.
        where: SCIM ``--where`` filter expression.
        criteria_file: Path to a JSON SearchCriteria payload, mutually
            exclusive with the expression and sort/paging flags.
        sort: Repeatable ``field[:asc|desc]`` sort expressions.
        page_no: Page number, defaults to 0 when omitted.
        page_size: Results per page, defaults to 20 when omitted.

    Returns:
        The assembled SearchCriteria.
    """
    if criteria_file is not None:
        _reject_expression_flags([status, effect, text, tag, field, where])
        _reject_sort_and_paging(sort=sort, page_no=page_no, page_size=page_size)
        return SearchCriteria.from_payload(_load_criteria_file(criteria_file))
    criteria = SearchCriteria()
    _apply_shorthands(criteria, status=status, effect=effect, text=text, tag=tag)
    for field_expr in field or []:
        criteria.filter_field(parse_field_expr(field_expr))
    _apply_where(criteria, where)
    for sort_spec in sort or []:
        sort_field, sort_order = _parse_sort(sort_spec)
        criteria.sort_by(sort_field, sort_order)
    criteria.page(
        page_no=_DEFAULT_PAGE_NO if page_no is None else page_no,
        page_size=_DEFAULT_PAGE_SIZE if page_size is None else page_size,
    )
    return criteria


def _reject_expression_flags(flag_values: list[object]) -> None:
    provided = [flag for flag, is_set in zip(_EXPRESSION_FLAGS, flag_values) if is_set]
    if provided:
        joined = ", ".join(provided)
        raise SearchExpressionError(
            f"--criteria-file cannot be combined with {joined}",
        )


def _reject_sort_and_paging(
    *,
    sort: list[str] | None,
    page_no: int | None,
    page_size: int | None,
) -> None:
    provided = []
    if sort:
        provided.append("--sort")
    if page_no is not None:
        provided.append("--page-no")
    if page_size is not None:
        provided.append("--page-size")
    if provided:
        joined = ", ".join(provided)
        raise SearchExpressionError(
            f"--criteria-file cannot be combined with {joined}",
        )


def _load_criteria_file(criteria_file: Path) -> dict[str, object]:
    try:
        payload = json.loads(criteria_file.read_text(encoding=_UTF8))
    except (OSError, json.JSONDecodeError) as exc:
        raise SearchExpressionError(
            f"could not read criteria file {criteria_file}: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise SearchExpressionError(
            f"criteria file {criteria_file} must contain a JSON object",
        )
    return payload


def _parse_sort(sort_spec: str) -> tuple[str, SortOrder]:
    field_name, _, order_token = sort_spec.partition(":")
    if not order_token:
        return field_name, SortOrder.DESC
    try:
        return field_name, SortOrder[order_token.upper()]
    except KeyError as exc:
        raise SearchExpressionError(
            f"invalid sort order {order_token!r}; use 'asc' or 'desc'",
        ) from exc


def _apply_shorthands(
    criteria: SearchCriteria,
    *,
    status: str | None,
    effect: str | None,
    text: str | None,
    tag: str | None,
) -> None:
    if status:
        criteria.filter_status(status)
    if effect:
        criteria.filter_effect_type(effect)
    if text:
        criteria.filter_text(text)
    if tag:
        criteria.filter_tags(tag)


def _apply_where(criteria: SearchCriteria, where: str | None) -> None:
    if not where:
        return
    for where_field in transpile_where(where):
        criteria.filter_field(where_field)
