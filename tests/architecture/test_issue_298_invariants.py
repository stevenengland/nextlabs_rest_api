"""Architectural invariants for issue #298.

Pins the paginated-endpoint engine contracts (PRD #298, decision D7) across
every migrated ``_cloudaz`` service, now that #299-#303 have moved all
paginated families onto it: no module hand-rolls a ``PageResult(...)``
outside the engine's own assembler, and every migrated sync/async service
pair shares a single ``PaginatedSpec`` constant per endpoint rather than
carrying divergent per-class definitions.
"""

from __future__ import annotations

import importlib
import re
import types
from pathlib import Path

_HAND_ROLLED_PAGE_RESULT = re.compile(r"PageResult\s*\(")

_cloudaz_file = importlib.import_module("nextlabs_sdk._cloudaz").__file__
if _cloudaz_file is None:
    raise RuntimeError("nextlabs_sdk._cloudaz has no filesystem location")
_CLOUDAZ_PKG_DIR = Path(_cloudaz_file).parent

# Non-service infrastructure files under `_cloudaz/`: `_response.py` owns the
# shared low-level parsers (including the one legitimate `PageResult(...)`
# construction that `assemble_page()` delegates to) and `_models.py` is a bare
# data-model module. Neither exposes a service class registered on a client.
_NON_SERVICE_MODULES = frozenset(("__init__.py", "_response.py", "_models.py"))

# Every other direct module file under `_cloudaz/` is a candidate paginated
# service module. `_engine/` owns the sanctioned `PageResult` assembler and
# `_search/` is the pure search-expression grammar — neither is a service
# module.
_SERVICE_MODULE_PATHS = tuple(
    sorted(
        path
        for path in _CLOUDAZ_PKG_DIR.glob("*.py")
        if path.name not in _NON_SERVICE_MODULES
    ),
)

# The sync/async service class pairs migrated onto the engine so far
# (#299-#303). Each entry names the owning module and its two classes.
_MIGRATED_SERVICE_PAIRS = (
    (
        "nextlabs_sdk._cloudaz._component_search",
        "ComponentSearchService",
        "AsyncComponentSearchService",
    ),
    (
        "nextlabs_sdk._cloudaz._component_type_search",
        "ComponentTypeSearchService",
        "AsyncComponentTypeSearchService",
    ),
    (
        "nextlabs_sdk._cloudaz._policy_search",
        "PolicySearchService",
        "AsyncPolicySearchService",
    ),
    ("nextlabs_sdk._cloudaz._tags", "TagService", "AsyncTagService"),
    (
        "nextlabs_sdk._cloudaz._reports",
        "PolicyActivityReportService",
        "AsyncPolicyActivityReportService",
    ),
    (
        "nextlabs_sdk._cloudaz._audit_logs",
        "EntityAuditLogService",
        "AsyncEntityAuditLogService",
    ),
    (
        "nextlabs_sdk._cloudaz._reporter_audit_logs",
        "ReporterAuditLogService",
        "AsyncReporterAuditLogService",
    ),
    (
        "nextlabs_sdk._cloudaz._activity_logs_service",
        "ReportActivityLogService",
        "AsyncReportActivityLogService",
    ),
)


def _spec_names_referenced(method: types.FunctionType) -> set[str]:
    """Return the module-level ``*_SPEC`` constant names a method's body reads."""
    return {name for name in method.__code__.co_names if name.endswith("_SPEC")}


def _engine_backed_method_names(cls: type) -> set[str]:
    """Return public method names on ``cls`` that reference a ``*_SPEC`` constant."""
    return {
        name
        for name, member in vars(cls).items()
        if not name.startswith("_")
        and isinstance(member, types.FunctionType)
        and _spec_names_referenced(member)
    }


def test_no_cloudaz_service_module_hand_rolls_page_result():
    assert _SERVICE_MODULE_PATHS, "no _cloudaz service modules discovered"
    for module_path in _SERVICE_MODULE_PATHS:
        source = module_path.read_text(encoding="utf-8")
        assert not _HAND_ROLLED_PAGE_RESULT.search(source), (
            f"{module_path.name} hand-rolls PageResult(...) instead of "
            "delegating to the engine's assemble_page()"
        )


def test_every_migrated_pair_shares_one_spec_constant_per_endpoint():
    for module_name, sync_name, async_name in _MIGRATED_SERVICE_PAIRS:
        module = importlib.import_module(module_name)
        sync_cls = getattr(module, sync_name)
        async_cls = getattr(module, async_name)
        method_names = _engine_backed_method_names(
            sync_cls,
        ) | _engine_backed_method_names(async_cls)
        assert method_names, f"{sync_name} has no engine-backed paginated method"
        for method_name in method_names:
            assert hasattr(sync_cls, method_name) and hasattr(
                async_cls,
                method_name,
            ), (
                f"{method_name} is engine-backed on only one of "
                f"{sync_name}/{async_name} — sync/async parity is broken"
            )
            sync_specs = _spec_names_referenced(getattr(sync_cls, method_name))
            async_specs = _spec_names_referenced(getattr(async_cls, method_name))
            assert sync_specs == async_specs, (
                f"{sync_name}.{method_name} and {async_name}.{method_name} "
                "must reference the same shared spec constant"
            )
            assert len(sync_specs) == 1, (
                f"{sync_name}.{method_name} must reference exactly one "
                "shared spec constant, not a divergent per-class definition"
            )
            # Both classes live in the same module (see _MIGRATED_SERVICE_PAIRS),
            # so the shared name already resolves to one module-level object;
            # confirm the constant actually exists there rather than trusting
            # the name alone.
            spec_name = next(iter(sync_specs))
            assert hasattr(module, spec_name), (
                f"{spec_name} referenced by {method_name} is not a "
                f"module-level constant on {module_name}"
            )
