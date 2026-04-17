from __future__ import annotations

import json
from typing import Any

from mockito import mock, when
import pytest
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


@pytest.mark.parametrize(
    "extra_opts,assertions",
    [
        pytest.param(
            (),
            lambda out: ("dept" in out) and ("Department" in out),
            id="table-output",
        ),
        pytest.param(
            (
                "--output",
                "json",
            ),
            lambda out: json.loads(out)[0]["key"] == "dept",
            id="json-output",
        ),
    ],
)
def test_tags_list_output(extra_opts, assertions):
    _, mock_tags = _stub_client()
    paginator = _make_paginator([_make_tag()])
    when(mock_tags).list(TagType.COMPONENT).thenReturn(paginator)

    result = runner.invoke(
        app,
        [*_GLOBAL_OPTS, *extra_opts, "tags", "list", "COMPONENT_TAG"],
    )

    assert result.exit_code == 0
    assert assertions(result.output)


def test_tags_list_case_insensitive():
    _, mock_tags = _stub_client()
    paginator = _make_paginator([_make_tag()])
    when(mock_tags).list(TagType.COMPONENT).thenReturn(paginator)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "list", "component_tag"])

    assert result.exit_code == 0


def test_tags_list_invalid_type():
    _stub_client()

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "list", "INVALID_TAG"])

    assert result.exit_code == 1
    assert "Invalid tag type" in result.output


@pytest.mark.parametrize(
    "extra_opts,assertion",
    [
        pytest.param((), lambda out: "dept" in out, id="table-output"),
        pytest.param(
            (
                "--output",
                "json",
            ),
            lambda out: json.loads(out)["id"] == 10,
            id="json-output",
        ),
    ],
)
def test_tags_get_output(extra_opts, assertion):
    _, mock_tags = _stub_client()
    when(mock_tags).get(10).thenReturn(_make_tag())

    result = runner.invoke(app, [*_GLOBAL_OPTS, *extra_opts, "tags", "get", "10"])

    assert result.exit_code == 0
    assert assertion(result.output)


def test_tags_get_not_found():
    _, mock_tags = _stub_client()
    when(mock_tags).get(999).thenRaise(NotFoundError(message="HTTP 404"))

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "get", "999"])

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_tags_create_success():
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


def test_tags_delete_success():
    _, mock_tags = _stub_client()
    when(mock_tags).delete(10).thenReturn(None)

    result = runner.invoke(app, [*_GLOBAL_OPTS, "tags", "delete", "10"])

    assert result.exit_code == 0
    assert "Deleted" in result.output or "deleted" in result.output
