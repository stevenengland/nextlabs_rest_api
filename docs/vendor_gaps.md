# Vendor gaps

This file records CloudAz behaviours the SDK relies on that are absent from,
or inconsistent with, the vendor OpenAPI spec
(`https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json`). Each
entry exists because the SDK has to model a real server behaviour that the
published contract does not describe.

## Endpoint — policy revision history

`GET /console/api/v1/policy/mgmt/history/{policyId}` is not present in the
vendor OpenAPI spec. It returns the standard paginated envelope
(`pageNo` / `pageSize` / `totalPages` / `totalNoOfRecords`) wrapping a list of
revision-metadata objects. On this list view `policyDetail` is always `null`;
only the per-revision metadata is populated.

Consumed by `PolicyService.list_history` / `AsyncPolicyService.list_history`,
which deserialize each entry into `PolicyHistoryEntry`.

## Opaque `actionType` codes

Revision entries carry an `actionType` string whose code meanings are
undocumented by the vendor (observed values include `UN` and `DE`). The SDK
exposes it as a plain `str`; it deliberately does not interpret the codes or
map them to an enum, because the value space and semantics are unknown.
