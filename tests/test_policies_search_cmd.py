from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mockito import ANY, mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._search import SearchCriteria
from nextlabs_sdk._pagination import PageResult, SyncPaginator
from nextlabs_sdk.cloudaz import (
    CloudAzClient,
    PolicyLite,
    PolicySearchService,
)

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


@pytest.fixture
def search_stub() -> tuple[Any, list[SearchCriteria]]:
    captured: list[SearchCriteria] = []
    mock_client = mock(CloudAzClient)
    mock_search = mock(PolicySearchService)
    mock_client.policy_search = mock_search

    def _answer(criteria: SearchCriteria) -> SyncPaginator[PolicyLite]:
        captured.append(criteria)
        return _make_paginator([_make_policy_lite()])

    when(mock_search).search(ANY).thenAnswer(_answer)
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_search, captured


def _make_policy_lite() -> PolicyLite:
    return PolicyLite(
        id=82,
        folder_id=1,
        name="Allow IT Access",
        lowercase_name="allow it access",
        policy_full_name="Allow IT Access",
        description="Allow IT dept access",
        status="DRAFT",
        effect_type="ALLOW",
        last_updated_date=0,
        created_date=0,
        has_parent=False,
        has_sub_policies=False,
        owner_id=1,
        owner_display_name="admin",
        modified_by_id=1,
        modified_by="admin",
        tags=[],
        no_of_tags=0,
        authorities=[],
        manual_deploy=False,
        deployment_time=0,
        deployed=False,
        revision_count=0,
        hide_more_details=False,
        deployment_pending=False,
    )


def _make_paginator(items: list[PolicyLite]) -> SyncPaginator[PolicyLite]:
    page = PageResult(
        entries=items,
        page_no=0,
        page_size=len(items),
        total_pages=1,
        total_records=len(items),
    )

    def fetch_page(page_no: int) -> PageResult[PolicyLite]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


def _fields(criteria: SearchCriteria) -> list[dict[str, Any]]:
    return criteria.to_dict()["criteria"]["fields"]


def test_field_option_issues_single_exact_match_and_renders_rows(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when searching with a single bare --field expression
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search", "--field", "status=DRAFT"],
    )

    # then the result rows render and the criteria carry a SINGLE_EXACT_MATCH field
    assert result.exit_code == 0
    assert "Allow IT Access" in result.output
    assert _fields(captured[0]) == [
        {
            "field": "status",
            "type": "SINGLE_EXACT_MATCH",
            "value": {"type": "String", "value": "DRAFT"},
        },
    ]


def test_repeated_field_options_and_into_one_payload(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when passing two --field flags
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--field",
            "status=DRAFT",
            "--field",
            "effectType=ALLOW",
        ],
    )

    # then both fields are ANDed together in a single criteria payload
    assert result.exit_code == 0
    fields = _fields(captured[0])
    assert {entry["field"] for entry in fields} == {"status", "effectType"}
    assert len(fields) == 2


def test_unknown_field_type_token_exits_with_error(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub
    _, captured = search_stub

    # when passing a --field with an unknown :TYPE token
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search", "--field", "status:BOGUS=DRAFT"],
    )

    # then the command exits non-zero and no search is issued
    assert result.exit_code != 0
    assert captured == []


def test_shorthand_status_flag_keeps_original_criteria(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when searching with the shorthand --status flag
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search", "--status", "DRAFT"],
    )

    # then the original MULTI status criteria are produced unchanged
    assert result.exit_code == 0
    assert _fields(captured[0]) == [
        {
            "field": "status",
            "type": "MULTI",
            "value": {"type": "String", "value": ["DRAFT"]},
        },
    ]


def test_where_option_issues_search_and_renders_rows(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when searching with a scalar --where SCIM filter
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search", "--where", 'status eq "DRAFT"'],
    )

    # then the rows render and the criteria carry the transpiled field
    assert result.exit_code == 0
    assert "Allow IT Access" in result.output
    assert _fields(captured[0]) == [
        {
            "field": "status",
            "type": "SINGLE_EXACT_MATCH",
            "value": {"type": "String", "value": "DRAFT"},
        },
    ]


def test_where_and_chain_ands_into_one_payload(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when searching with an and-chained --where filter
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--where",
            'status eq "DRAFT" and effectType eq "ALLOW"',
        ],
    )

    # then both terms AND together in one criteria payload
    assert result.exit_code == 0
    fields = _fields(captured[0])
    assert {entry["field"] for entry in fields} == {"status", "effectType"}
    assert len(fields) == 2


def test_where_cross_field_or_exits_with_error(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub
    _, captured = search_stub

    # when passing a cross-field OR --where filter
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--where",
            'status eq "DRAFT" or name co "Allow"',
        ],
    )

    # then the command exits non-zero and no search is issued
    assert result.exit_code != 0
    assert captured == []


def _sort_fields(criteria: SearchCriteria) -> list[dict[str, str]]:
    return criteria.to_dict()["criteria"]["sortFields"]


def _criteria_body(criteria: SearchCriteria) -> dict[str, Any]:
    return criteria.to_dict()["criteria"]


def test_criteria_file_posts_payload_verbatim_and_renders_rows(
    search_stub: tuple[Any, list[SearchCriteria]],
    tmp_path: Path,
) -> None:
    # given a criteria file holding a verbatim SearchCriteria payload
    _, captured = search_stub
    payload = {
        "criteria": {
            "fields": [
                {
                    "field": "status",
                    "type": "MULTI",
                    "value": {"type": "String", "value": ["DRAFT"]},
                },
            ],
            "sortFields": [{"field": "name", "order": "ASC"}],
            "pageNo": 3,
            "pageSize": 50,
        },
    }
    criteria_file = tmp_path / "criteria.json"
    criteria_file.write_text(json.dumps(payload), encoding="utf-8")

    # when searching with --criteria-file
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--criteria-file",
            str(criteria_file),
        ],
    )

    # then the rows render and the file's criteria are posted verbatim
    assert result.exit_code == 0
    assert "Allow IT Access" in result.output
    assert captured[0].to_dict() == payload


def test_criteria_file_with_expression_flag_exits_with_error(
    search_stub: tuple[Any, list[SearchCriteria]],
    tmp_path: Path,
) -> None:
    # given a valid criteria file
    _, captured = search_stub
    criteria_file = tmp_path / "criteria.json"
    criteria_file.write_text(
        json.dumps({"criteria": {"fields": []}}),
        encoding="utf-8",
    )

    # when combining --criteria-file with an expression flag
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--criteria-file",
            str(criteria_file),
            "--where",
            'status eq "DRAFT"',
        ],
    )

    # then the command exits non-zero and no search is issued
    assert result.exit_code != 0
    assert captured == []


@pytest.mark.parametrize(
    "extra_flags",
    [
        ["--sort", "name:asc"],
        ["--page-no", "2"],
        ["--page-size", "50"],
    ],
)
def test_criteria_file_with_sort_or_paging_flag_exits_with_error(
    search_stub: tuple[Any, list[SearchCriteria]],
    tmp_path: Path,
    extra_flags: list[str],
) -> None:
    # given a valid criteria file
    _, captured = search_stub
    criteria_file = tmp_path / "criteria.json"
    criteria_file.write_text(
        json.dumps({"criteria": {"fields": []}}),
        encoding="utf-8",
    )

    # when combining --criteria-file with a sort or paging flag
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--criteria-file",
            str(criteria_file),
            *extra_flags,
        ],
    )

    # then the command exits non-zero and no search is issued
    assert result.exit_code != 0
    assert captured == []


def test_repeated_sort_options_preserve_order_and_explicit_direction(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when passing two --sort flags with explicit directions
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--sort",
            "name:asc",
            "--sort",
            "lastUpdatedDate:desc",
        ],
    )

    # then the sort fields keep their order and directions
    assert result.exit_code == 0
    assert _sort_fields(captured[0]) == [
        {"field": "name", "order": "ASC"},
        {"field": "lastUpdatedDate", "order": "DESC"},
    ]


def test_bare_sort_option_defaults_to_descending(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when passing a bare --sort field with no direction
    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "policies", "search", "--sort", "name"],
    )

    # then the field sorts descending by default
    assert result.exit_code == 0
    assert _sort_fields(captured[0]) == [{"field": "name", "order": "DESC"}]


def test_page_no_and_page_size_set_pagination_fields(
    search_stub: tuple[Any, list[SearchCriteria]],
) -> None:
    # given a search stub capturing the built criteria
    _, captured = search_stub

    # when passing --page-no and --page-size
    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "policies",
            "search",
            "--page-no",
            "2",
            "--page-size",
            "5",
        ],
    )

    # then the criteria carry the requested pagination values
    assert result.exit_code == 0
    body = _criteria_body(captured[0])
    assert body["pageNo"] == 2
    assert body["pageSize"] == 5
