"""Architectural invariants for issue #95.

Pins the public CloudAz surface so the types that appear on
``ReporterAuditLogService`` and ``PolicySearchService`` stay importable
from ``nextlabs_sdk.cloudaz``, and keeps the OpenAPI-aligned name
``SavedReportCriteria`` in sync with its backward-compatible alias
``ReportCriteria``.
"""

from __future__ import annotations

import importlib


def test_reporter_audit_log_entry_is_publicly_re_exported() -> None:
    module = importlib.import_module("nextlabs_sdk.cloudaz")
    from nextlabs_sdk._cloudaz._reporter_audit_log_models import (
        ReporterAuditLogEntry as Internal,
    )

    assert module.ReporterAuditLogEntry is Internal


def test_saved_search_is_publicly_re_exported() -> None:
    module = importlib.import_module("nextlabs_sdk.cloudaz")
    from nextlabs_sdk._cloudaz._search import SavedSearch as Internal

    assert module.SavedSearch is Internal


def test_search_criteria_is_publicly_re_exported() -> None:
    module = importlib.import_module("nextlabs_sdk.cloudaz")
    from nextlabs_sdk._cloudaz._search import SearchCriteria as Internal

    assert module.SearchCriteria is Internal


def test_saved_report_criteria_is_publicly_re_exported() -> None:
    module = importlib.import_module("nextlabs_sdk.cloudaz")
    from nextlabs_sdk._cloudaz._report_models import (
        SavedReportCriteria as Internal,
    )

    assert module.SavedReportCriteria is Internal


def test_report_criteria_is_alias_for_saved_report_criteria() -> None:
    module = importlib.import_module("nextlabs_sdk.cloudaz")

    assert module.ReportCriteria is module.SavedReportCriteria


def test_saved_report_criteria_canonical_name_matches_openapi() -> None:
    from nextlabs_sdk._cloudaz._report_models import SavedReportCriteria

    assert SavedReportCriteria.__name__ == "SavedReportCriteria"
