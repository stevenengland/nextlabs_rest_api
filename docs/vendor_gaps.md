# Vendor gaps

This file records CloudAz behaviours the SDK relies on that are absent from,
or inconsistent with, the vendor OpenAPI spec
(`https://developer.nextlabs.com/assets/external/cloudaz/api-docs.json`). Each
entry exists because the SDK has to model a real server behaviour that the
published contract does not describe.

## Endpoint — policy revision history

`GET /console/api/v1/policy/mgmt/history/{policyId}` is not present in the
vendor OpenAPI spec. Although the response is wrapped in the standard paginated
envelope (`pageNo` / `pageSize` / `totalPages` / `totalNoOfRecords`), the
endpoint does **not** actually paginate: it ignores the `pageNo` / `pageSize`
query params and returns every revision in a single response. The three count
fields are all reported equal to the total record count — `pageSize`,
`totalPages`, and `totalNoOfRecords` move together (verified live up to 180
revisions returned in one shot). Treating them as real pagination cursors
causes the same body to be refetched once per record.

Because of this, `PolicyService.list_history` /
`AsyncPolicyService.list_history` issue a single GET with no query params and
return a plain `list[PolicyHistoryEntry]`. As a guard against the vendor ever
introducing real pagination, the SDK raises `ApiError` if a response ever
reports more `totalNoOfRecords` than it returned — at which point that returned
count reveals the page size that genuine pagination support must be built
around. On this list view `policyDetail` is always `null`; only the
per-revision metadata is populated.

## Endpoint — policy revision detail

`GET /console/api/v1/policy/mgmt/viewRevision/{revision_id}/{revision}` is not
present in the vendor OpenAPI spec. It returns the full revision detail object,
including the `policyDetail` payload, for a single revision identified by its
`revision_id` and `revision` number.

Consumed by `PolicyService.get_revision` / `AsyncPolicyService.get_revision`,
which deserialize the response into `PolicyRevision`.

## Endpoint — component revision history

`GET /console/api/v1/component/mgmt/history/{component_id}` is not present in
the vendor OpenAPI spec. Although the response is wrapped in the standard
paginated envelope (`pageNo` / `pageSize` / `totalPages` / `totalNoOfRecords`),
the endpoint does **not** actually paginate: it ignores the `pageNo` /
`pageSize` query params and returns every revision in a single response. The
three count fields are all reported equal to the total record count —
`pageSize`, `totalPages`, and `totalNoOfRecords` move together. Treating them
as real pagination cursors causes the same body to be refetched once per
record.

Because of this, `ComponentService.list_history` /
`AsyncComponentService.list_history` issue a single GET with no query params
and return a plain `list[ComponentHistoryEntry]`. As a guard against the vendor
ever introducing real pagination, the SDK raises `ApiError` if a response ever
reports more `totalNoOfRecords` than it returned — at which point that returned
count reveals the page size that genuine pagination support must be built
around. On this list view `componentDetail` is always `null`; only the
per-revision metadata is populated.

## Endpoint — component revision detail

`GET /console/api/v1/component/mgmt/viewRevision/{revision_id}/{revision}` is
not present in the vendor OpenAPI spec. It returns the full revision detail
object, including the `componentDetail` payload, for a single revision
identified by its `revision_id` and `revision` number.

Consumed by `ComponentService.get_revision` / `AsyncComponentService.get_revision`,
which deserialize the response into `ComponentRevision`.

**Deliberate URL divergence:** the live server path observed during e2e testing
contains an extra `revcollection` segment
(`.../viewRevision/revcollection/{revision_id}/{revision}`). The SDK drops this
segment to keep the URL shape consistent with the policy equivalent
(`/policy/mgmt/viewRevision/{revision_id}/{revision}`). The e2e flow verifies
the live path and confirms the server responds correctly without the extra
segment.

## Opaque `actionType` codes

Revision entries carry an `actionType` string whose code meanings are
undocumented by the vendor (observed values include `UN` and `DE`). The SDK
exposes it as a plain `str`; it deliberately does not interpret the codes or
map them to an enum, because the value space and semantics are unknown.
