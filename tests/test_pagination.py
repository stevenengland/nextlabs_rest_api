from __future__ import annotations

import asyncio

import pytest

from nextlabs_sdk._pagination import (
    AsyncPaginator,
    PageResult,
    SyncPaginator,
)


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


def test_page_result_is_frozen() -> None:
    page = _make_page(["a"])
    with pytest.raises(AttributeError):
        page.__setattr__("items", [])


def test_sync_paginator_single_page() -> None:
    page = _make_page(["a", "b"], total_records=2)

    def fetch(page_no: int) -> PageResult[str]:
        return page

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)
    results = list(paginator)

    assert results == ["a", "b"]


def test_sync_paginator_multiple_pages() -> None:
    pages = [
        _make_page(["a", "b"], page_no=0, total_pages=3, total_records=5),
        _make_page(["c", "d"], page_no=1, total_pages=3, total_records=5),
        _make_page(["e"], page_no=2, total_pages=3, total_records=5),
    ]

    def fetch(page_no: int) -> PageResult[str]:
        return pages[page_no]

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)
    results = list(paginator)

    assert results == ["a", "b", "c", "d", "e"]


def test_sync_paginator_empty_results() -> None:
    page = _make_page([], total_pages=0, total_records=0)

    def fetch(page_no: int) -> PageResult[str]:
        return page

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)
    results = list(paginator)

    assert results == []


def test_sync_paginator_total_after_first_page() -> None:
    page = _make_page(["a"], total_records=42)

    def fetch(page_no: int) -> PageResult[str]:
        return page

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)
    paginator.first_page()

    assert paginator.total == 42


def test_sync_paginator_total_before_fetch_raises() -> None:
    def fetch(page_no: int) -> PageResult[str]:
        return _make_page(["a"])

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)

    with pytest.raises(RuntimeError):
        getattr(paginator, "total")


def test_sync_paginator_first_page_returns_page_result() -> None:
    page = _make_page(["a", "b"], total_records=10)

    def fetch(page_no: int) -> PageResult[str]:
        return page

    paginator = SyncPaginator(fetch_page=fetch, page_size=2)
    first = paginator.first_page()

    assert first.entries == ["a", "b"]
    assert first.total_records == 10


def test_async_paginator_multiple_pages() -> None:
    pages = [
        _make_page(["a", "b"], page_no=0, total_pages=2, total_records=3),
        _make_page(["c"], page_no=1, total_pages=2, total_records=3),
    ]

    async def fetch(page_no: int) -> PageResult[str]:
        return pages[page_no]

    async def collect() -> list[str]:
        paginator = AsyncPaginator(fetch_page=fetch, page_size=2)
        return [each_item async for each_item in paginator]

    results = asyncio.run(collect())

    assert results == ["a", "b", "c"]


def test_async_paginator_total_after_first_page() -> None:
    page = _make_page(["a"], total_records=99)

    async def fetch(page_no: int) -> PageResult[str]:
        return page

    async def run() -> int:
        paginator = AsyncPaginator(fetch_page=fetch, page_size=2)
        await paginator.first_page()
        return paginator.total

    assert asyncio.run(run()) == 99


def test_async_paginator_empty_results() -> None:
    page = _make_page([], total_pages=0, total_records=0)

    async def fetch(page_no: int) -> PageResult[str]:
        return page

    async def collect() -> list[str]:
        paginator = AsyncPaginator(fetch_page=fetch, page_size=2)
        return [each_item async for each_item in paginator]

    assert asyncio.run(collect()) == []
