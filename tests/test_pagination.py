from __future__ import annotations

import asyncio
from typing import Sequence

import pytest

from nextlabs_sdk._pagination import AsyncPaginator, PageResult, SyncPaginator


def _make_page(
    items: list[str],
    page_no: int = 0,
    page_size: int = 2,
    total_pages: int = 1,
    total_records: int = 2,
) -> PageResult[str]:
    return PageResult(
        entries=items,
        page_no=page_no,
        page_size=page_size,
        total_pages=total_pages,
        total_records=total_records,
    )


def _sync_paginator(pages: Sequence[PageResult[str]]) -> SyncPaginator[str]:
    def fetch(page_no: int) -> PageResult[str]:
        return pages[page_no] if len(pages) > 1 else pages[0]

    return SyncPaginator(fetch_page=fetch)


def _async_paginator(pages: Sequence[PageResult[str]]) -> AsyncPaginator[str]:
    async def fetch(page_no: int) -> PageResult[str]:
        return pages[page_no] if len(pages) > 1 else pages[0]

    return AsyncPaginator(fetch_page=fetch)


def _assert_sync_yields(pages: Sequence[PageResult[str]], expected: list[str]) -> None:
    assert list(_sync_paginator(pages)) == expected


def _assert_async_yields(pages: Sequence[PageResult[str]], expected: list[str]) -> None:
    async def collect() -> list[str]:
        return [item async for item in _async_paginator(pages)]

    assert asyncio.run(collect()) == expected


def test_page_result_is_frozen():
    page = _make_page(["a"])
    with pytest.raises(AttributeError):
        page.__setattr__("items", [])


def test_sync_paginator_single_page():
    _assert_sync_yields([_make_page(["a", "b"], total_records=2)], ["a", "b"])


def test_sync_paginator_multiple_pages():
    pages = [
        _make_page(["a", "b"], page_no=0, total_pages=3, total_records=5),
        _make_page(["c", "d"], page_no=1, total_pages=3, total_records=5),
        _make_page(["e"], page_no=2, total_pages=3, total_records=5),
    ]
    _assert_sync_yields(pages, ["a", "b", "c", "d", "e"])


def test_sync_paginator_empty_results():
    _assert_sync_yields([_make_page([], total_pages=0, total_records=0)], [])


def test_sync_paginator_total_after_first_page():
    paginator = _sync_paginator([_make_page(["a"], total_records=42)])
    paginator.first_page()
    assert paginator.total == 42


def test_sync_paginator_total_before_fetch_raises():
    paginator = _sync_paginator([_make_page(["a"])])
    with pytest.raises(RuntimeError):
        getattr(paginator, "total")


def test_sync_paginator_first_page_returns_page_result():
    paginator = _sync_paginator([_make_page(["a", "b"], total_records=10)])
    first = paginator.first_page()

    assert first.entries == ["a", "b"]
    assert first.total_records == 10


def test_async_paginator_multiple_pages():
    pages = [
        _make_page(["a", "b"], page_no=0, total_pages=2, total_records=3),
        _make_page(["c"], page_no=1, total_pages=2, total_records=3),
    ]
    _assert_async_yields(pages, ["a", "b", "c"])


def test_async_paginator_total_after_first_page():
    async def run() -> int:
        paginator = _async_paginator([_make_page(["a"], total_records=99)])
        await paginator.first_page()
        return paginator.total

    assert asyncio.run(run()) == 99


def test_async_paginator_empty_results():
    _assert_async_yields([_make_page([], total_pages=0, total_records=0)], [])
