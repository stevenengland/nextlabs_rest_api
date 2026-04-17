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
