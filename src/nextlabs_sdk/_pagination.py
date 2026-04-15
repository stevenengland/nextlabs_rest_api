from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

_ItemT = TypeVar("_ItemT")

_AsyncFetchPage = Callable[[int], Awaitable["PageResult[_ItemT]"]]


@dataclass(frozen=True)
class PageResult(Generic[_ItemT]):
    """A single page of results from a paginated API endpoint."""

    entries: list[_ItemT]
    page_no: int
    page_size: int
    total_pages: int
    total_records: int


class SyncPaginator(Generic[_ItemT]):
    """Sync iterator over paginated API results."""

    def __init__(
        self,
        fetch_page: Callable[[int], PageResult[_ItemT]],
    ) -> None:
        self._fetch_page = fetch_page
        self._total: int | None = None

    @property
    def total(self) -> int:
        if self._total is None:
            msg = "Total is not available until the first page is fetched"
            raise RuntimeError(msg)
        return self._total

    def first_page(self) -> PageResult[_ItemT]:
        page = self._fetch_page(0)
        self._total = page.total_records
        return page

    def __iter__(self) -> Iterator[_ItemT]:
        current_page_no = 0

        while True:
            page = self._fetch_page(current_page_no)
            self._total = page.total_records

            yield from page.entries

            current_page_no += 1
            if current_page_no >= page.total_pages:
                break


class AsyncPaginator(Generic[_ItemT]):
    """Async iterator over paginated API results."""

    def __init__(
        self,
        fetch_page: _AsyncFetchPage[_ItemT],
    ) -> None:
        self._fetch_page = fetch_page
        self._total: int | None = None

    @property
    def total(self) -> int:
        if self._total is None:
            msg = "Total is not available until the first page is fetched"
            raise RuntimeError(msg)
        return self._total

    async def first_page(self) -> PageResult[_ItemT]:
        page = await self._fetch_page(0)
        self._total = page.total_records
        return page

    async def __aiter__(self) -> AsyncIterator[_ItemT]:
        current_page_no = 0

        while True:
            page = await self._fetch_page(current_page_no)
            self._total = page.total_records

            for page_item in page.entries:
                yield page_item

            current_page_no += 1
            if current_page_no >= page.total_pages:
                break
