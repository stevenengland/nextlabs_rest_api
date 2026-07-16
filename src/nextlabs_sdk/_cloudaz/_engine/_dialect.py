from __future__ import annotations

import enum
from dataclasses import dataclass


class PageShape(enum.Enum):
    """The three response shape-families a paginated endpoint may use."""

    CLASSIC_ENVELOPE = "classic_envelope"
    REPORTER_ENVELOPE = "reporter_envelope"
    PAGEABLE = "pageable"


@dataclass(frozen=True)
class PageDialect:
    """The paging query-parameter vocabulary for a page shape-family."""

    shape: PageShape
    page_param: str = "pageNo"
    size_param: str = "pageSize"


CLASSIC_ENVELOPE = PageDialect(PageShape.CLASSIC_ENVELOPE)
REPORTER_ENVELOPE = PageDialect(PageShape.REPORTER_ENVELOPE, "page", "size")
PAGEABLE = PageDialect(PageShape.PAGEABLE, "page", "size")
