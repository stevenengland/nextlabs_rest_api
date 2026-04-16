from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
from typer.testing import CliRunner

from nextlabs_sdk._cli import _client_factory
from nextlabs_sdk._cli._app import app
from nextlabs_sdk._cloudaz._client import CloudAzClient
from nextlabs_sdk._cloudaz._models import Tag, TagType
from nextlabs_sdk._cloudaz._tags import TagService
from nextlabs_sdk._pagination import PageResult, SyncPaginator
from nextlabs_sdk.exceptions import NotFoundError

runner = CliRunner()

_GLOBAL_OPTS = (
    "--base-url",
    "https://example.com",
    "--username",
    "admin",
    "--password",
    "secret",
)


def _make_tag(
    tag_id: int = 10,
    key: str = "dept",
    label: str = "Department",
) -> Tag:
    return Tag(
        id=tag_id,
        key=key,
        label=label,
        type=TagType.COMPONENT,
        status="ACTIVE",
    )


def _stub_client() -> tuple[Any, Any]:
    mock_client = mock(CloudAzClient)
    mock_tags = mock(TagService)
    mock_client.tags = mock_tags
    when(_client_factory).make_cloudaz_client(...).thenReturn(mock_client)
    return mock_client, mock_tags


def _make_paginator(tags: list[Tag]) -> SyncPaginator[Tag]:
    page = PageResult(
        entries=tags,
        page_no=0,
        page_size=len(tags),
        total_pages=1,
        total_records=len(tags),
    )

    def fetch_page(page_no: int) -> PageResult[Tag]:
        return page

    return SyncPaginator(fetch_page=fetch_page)


def test_tags_list_table_output() -> None:
    _, mock_tags = _stub_client()
    tag = _make_tag()
    paginator = _make_paginator([tag])
    when(mock_tags).list(TagType.COMPONENT).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "tags", "list", "COMPONENT_TAG"],
    )

    assert result.exit_code == 0
    assert "dept" in result.output
    assert "Department" in result.output


def test_tags_list_json_output() -> None:
    _, mock_tags = _stub_client()
    tag = _make_tag()
    paginator = _make_paginator([tag])
    when(mock_tags).list(TagType.COMPONENT).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "--json", "tags", "list", "COMPONENT_TAG"],
    )

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["key"] == "dept"


def test_tags_list_case_insensitive() -> None:
    _, mock_tags = _stub_client()
    paginator = _make_paginator([_make_tag()])
    when(mock_tags).list(TagType.COMPONENT).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "tags", "list", "component_tag"],
    )

    assert result.exit_code == 0


def test_tags_list_invalid_type() -> None:
    _stub_client()

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, "tags", "list", "INVALID_TAG"],
    )

    assert result.exit_code == 1
    assert "Invalid tag type" in result.output


def test_tags_get_table_output() -> None:
    _, mock_tags = _stub_client()
    tag = _make_tag()
    when(mock_tags).get(10).thenReturn(tag)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "get", "10"])

    assert result.exit_code == 0
    assert "dept" in result.output


def test_tags_get_json_output() -> None:
    _, mock_tags = _stub_client()
    tag = _make_tag()
    when(mock_tags).get(10).thenReturn(tag)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "--json", "tags", "get", "10"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == 10


def test_tags_get_not_found() -> None:
    _, mock_tags = _stub_client()
    when(mock_tags).get(999).thenRaise(
        NotFoundError(message="HTTP 404"),
    )

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_tags_create_success() -> None:
    _, mock_tags = _stub_client()
    when(mock_tags).create(
        TagType.POLICY,
        key="env",
        label="Environment",
    ).thenReturn(42)

    result = runner.invoke(
        app,
        [
            *_GLOBAL_OPTS,
            "tags",
            "create",
            "POLICY_TAG",
            "--key",
            "env",
            "--label",
            "Environment",
        ],
    )

    assert result.exit_code == 0
    assert "42" in result.output


def test_tags_delete_success() -> None:
    _, mock_tags = _stub_client()
    when(mock_tags).delete(10).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "delete", "10"])

    assert result.exit_code == 0
    assert "Deleted" in result.output or "deleted" in result.output
