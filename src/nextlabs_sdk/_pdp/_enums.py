from __future__ import annotations

from enum import Enum


class ContentType(str, Enum):
    JSON = "application/json"
    XML = "application/xml"


class Decision(str, Enum):
    PERMIT = "Permit"
    DENY = "Deny"
    NOT_APPLICABLE = "NotApplicable"
    INDETERMINATE = "Indeterminate"


class ResourceDimension(str, Enum):
    FROM = "from"
    TO = "to"
