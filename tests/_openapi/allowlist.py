"""Allowlist of ``(path, method, status)`` triples that cannot round-trip.

Each triple is tagged with a reason so regressions in the round-trip
suite stay honest: when the SDK gains a model or the spec fixture is
refreshed with valid JSON, the corresponding entry must be removed.

Categories
----------

* ``INVALID_JSON_EXAMPLES`` — the vendor spec's example body is not
  parseable JSON (unquoted strings, trailing commas, etc.). Nothing the
  SDK can do here; the fix is upstream or in the fixture. These stay
  xfailed until the spec is corrected.
* ``MISSING_MODEL`` — the SDK does not (yet) expose a dedicated Pydantic
  response model for this endpoint. The round-trip suite cannot assert
  a contract on it. Removing the entry is the signal that a model has
  been added; wire it up in :mod:`tests._openapi.model_registry` at the
  same time.
"""

from __future__ import annotations

INVALID_JSON_EXAMPLES: frozenset[tuple[str, str, str]] = frozenset(
    (
        ("/console/api/v1/component/mgmt/bulkDelete", "delete", "200"),
        ("/console/api/v1/component/mgmt/deploy", "post", "200"),
        ("/console/api/v1/component/mgmt/findDependencies", "post", "200"),
        ("/console/api/v1/component/mgmt/remove/{id}", "delete", "200"),
        ("/console/api/v1/component/mgmt/unDeploy", "post", "200"),
        ("/console/api/v1/component/search/remove/{id}", "delete", "200"),
        ("/console/api/v1/config/dataType/list", "get", "200"),
        ("/console/api/v1/config/tags/remove/{id}", "delete", "200"),
        ("/console/api/v1/policy/mgmt/bulkDelete", "delete", "200"),
        (
            "/console/api/v1/policy/mgmt/bulkDeleteXacmlPolicy",
            "delete",
            "200",
        ),
        ("/console/api/v1/policy/mgmt/deploy", "post", "200"),
        (
            "/console/api/v1/policy/mgmt/obligation/daeValidate",
            "post",
            "200",
        ),
        ("/console/api/v1/policy/mgmt/remove/{id}", "delete", "200"),
        ("/console/api/v1/policy/mgmt/unDeploy", "post", "200"),
        ("/console/api/v1/policy/search/remove/{id}", "delete", "200"),
        ("/console/api/v1/policyModel/mgmt/active/{id}", "get", "200"),
        ("/console/api/v1/policyModel/mgmt/bulkDelete", "delete", "200"),
        (
            "/console/api/v1/policyModel/mgmt/extraSubjectAttribs/{type}",
            "get",
            "200",
        ),
        ("/console/api/v1/policyModel/mgmt/remove/{id}", "delete", "200"),
        ("/console/api/v1/policyModel/mgmt/{id}", "get", "200"),
        ("/console/api/v1/policyModel/search/remove/{id}", "delete", "200"),
        ("/console/scim/v2/Bulk", "post", "200"),
    ),
)


MISSING_MODEL: frozenset[tuple[str, str, str]] = frozenset(
    (
        ("/console/api/v1/component/mgmt/add", "post", "200"),
        ("/console/api/v1/component/mgmt/addSubComponent", "post", "200"),
        ("/console/api/v1/component/mgmt/modify", "put", "200"),
        ("/console/api/v1/component/search", "post", "200"),
        ("/console/api/v1/component/search/add", "post", "200"),
        ("/console/api/v1/component/search/listNames/{group}", "get", "200"),
        (
            "/console/api/v1/component/search/listNames/{group}/{type}",
            "get",
            "200",
        ),
        ("/console/api/v1/component/search/saved/{id}", "get", "200"),
        ("/console/api/v1/component/search/savedlist", "get", "200"),
        ("/console/api/v1/component/search/savedlist/{name}", "get", "200"),
        ("/console/api/v1/config/dataType/list/{dataType}", "get", "200"),
        ("/console/api/v1/config/dataType/types", "get", "200"),
        ("/console/api/v1/config/tags/add/{tagType}", "post", "200"),
        ("/console/api/v1/policy/mgmt/add", "post", "200"),
        ("/console/api/v1/policy/mgmt/addSubPolicy", "post", "200"),
        ("/console/api/v1/policy/mgmt/export", "post", "200"),
        ("/console/api/v1/policy/mgmt/exportAll", "get", "200"),
        ("/console/api/v1/policy/mgmt/exportOptions", "get", "200"),
        ("/console/api/v1/policy/mgmt/generatePDF", "post", "200"),
        ("/console/api/v1/policy/mgmt/generateXACML", "post", "200"),
        ("/console/api/v1/policy/mgmt/import", "post", "200"),
        ("/console/api/v1/policy/mgmt/importXacmlPolicy", "post", "200"),
        ("/console/api/v1/policy/mgmt/modify", "put", "200"),
        ("/console/api/v1/policy/mgmt/retrieveAllPolicies", "get", "200"),
        ("/console/api/v1/policy/search", "post", "200"),
        ("/console/api/v1/policy/search/add", "post", "200"),
        ("/console/api/v1/policy/search/saved/{id}", "get", "200"),
        ("/console/api/v1/policy/search/savedlist", "get", "200"),
        ("/console/api/v1/policy/search/savedlist/{name}", "get", "200"),
        ("/console/api/v1/policy/search/{search}", "post", "200"),
        ("/console/api/v1/policyModel/mgmt/add", "post", "200"),
        ("/console/api/v1/policyModel/mgmt/clone", "post", "200"),
        ("/console/api/v1/policyModel/mgmt/modify", "put", "200"),
        ("/console/api/v1/policyModel/search", "post", "200"),
        ("/console/api/v1/policyModel/search/add", "post", "200"),
        ("/console/api/v1/policyModel/search/saved/{id}", "get", "200"),
        (
            "/console/api/v1/policyModel/search/savedlist/{type}",
            "get",
            "200",
        ),
        (
            "/console/api/v1/policyModel/search/savedlist/{type}/{name}",
            "get",
            "200",
        ),
        ("/console/scim/v2/Groups", "get", "200"),
        ("/console/scim/v2/Groups", "post", "201"),
        ("/console/scim/v2/Groups/{groupId}", "get", "200"),
        ("/console/scim/v2/Groups/{groupId}", "put", "200"),
        ("/console/scim/v2/Users", "get", "200"),
        ("/console/scim/v2/Users", "post", "201"),
        ("/console/scim/v2/Users/{userId}", "get", "200"),
        ("/console/scim/v2/Users/{userId}", "patch", "200"),
        ("/console/scim/v2/Users/{userId}", "put", "200"),
        ("/nextlabs-reporter/api/activity-logs/search", "get", "200"),
        (
            "/nextlabs-reporter/api/system-configuration/getUIConfigs",
            "get",
            "200",
        ),
        ("/nextlabs-reporter/api/v1/auditLogs/export", "post", "400"),
        ("/nextlabs-reporter/api/v1/auditLogs/export", "post", "500"),
        ("/nextlabs-reporter/api/v1/auditLogs/search", "post", "200"),
        ("/nextlabs-reporter/api/v1/auditLogs/users", "get", "200"),
        (
            "/nextlabs-reporter/api/v1/dashboard/activityByPolicies/{fromDate}/{toDate}/{policyDecision}",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/dashboard/activityByResources/{fromDate}/{toDate}/{policyDecision}",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/dashboard/activityByUsers/{fromDate}/{toDate}/{policyDecision}",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/dashboard/alertByMonitorTags/{fromDate}/{toDate}",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/dashboard/latestAlerts/{fromDate}/{toDate}",
            "get",
            "200",
        ),
        ("/nextlabs-reporter/api/v1/policy-activity-reports", "get", "200"),
        ("/nextlabs-reporter/api/v1/policy-activity-reports", "post", "200"),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/delete",
            "post",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/generate/enforcements",
            "post",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/generate/widgets",
            "post",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/mappings",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/policies",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/resource-actions",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/share/application-users",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/share/user-groups",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/users",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/{reportId}",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/{reportId}",
            "put",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/{reportId}/enforcements",
            "get",
            "200",
        ),
        (
            "/nextlabs-reporter/api/v1/policy-activity-reports/{reportId}/widgets",
            "get",
            "200",
        ),
        ("/nextlabs-reporter/api/v1/report-activity-logs", "post", "200"),
        (
            "/nextlabs-reporter/api/v1/report-activity-logs/{rowId}",
            "get",
            "200",
        ),
    ),
)


KNOWN_UNPARSEABLE: frozenset[tuple[str, str, str]] = (
    INVALID_JSON_EXAMPLES | MISSING_MODEL
)
