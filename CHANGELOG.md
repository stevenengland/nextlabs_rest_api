# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- `PolicyService.retrieve_all_policies` / `AsyncPolicyService.retrieve_all_policies` —
  wraps `GET /console/api/v1/policy/mgmt/retrieveAllPolicies` to export all policies
  with a selectable `ExportMode` (`PLAIN` or `SANDE`).
- `PolicySearchService.search_named` / `AsyncPolicySearchService.search_named` —
  wraps `POST /console/api/v1/policy/search/{search}` for named/scoped policy search
  variants (passes the `search` path segment through verbatim).
- `ReporterAuditLogService` / `AsyncReporterAuditLogService` exposed as
  `client.reporter_audit_logs`, wrapping `GET /nextlabs-reporter/api/activity-logs/search`
  for Reporter audit logs covering Policy Activity Reports, Monitors, and Alerts
  (distinct from the entity audit log). Includes a `ReporterAuditLogEntry` model.

### Changed

- Transport layer now wraps retry-exhausted `httpx` exceptions into the
  `NextLabsError` hierarchy: `httpx.ConnectTimeout` / `httpx.ReadTimeout` raise
  `RequestTimeoutError`, and `httpx.ConnectError` raises `TransportError`. SSL
  verification failures produce a `TransportError` with a hint pointing to
  `--no-verify` for dev / self-signed servers.
- CLI error handler now renders unexpected exceptions as a single-line message
  (exit code 1) instead of a full traceback, and adds dedicated prefixes for
  `TransportError` (*Connection error*) and `RequestTimeoutError` (*Request
  timed out*).
- JSON response decoding is now hardened across all call sites (CloudAz auth,
  PDP auth, CloudAz response envelope, PDP eval/permissions). Non-JSON 200
  bodies now raise `AuthenticationError` / `ApiError` with an *Invalid JSON
  response* message (body preview truncated to 500 chars) instead of leaking
  a bare `ValueError`. Missing or mistyped required keys raise
  `AuthenticationError` / `ApiError` with an *Unexpected response shape*
  message instead of a bare `KeyError` / `TypeError`.
