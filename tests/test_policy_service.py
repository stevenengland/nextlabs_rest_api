from __future__ import annotations

from typing import Any

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_models import (
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._policies import PolicyService
from nextlabs_sdk._cloudaz._policy_models import (
    ExportOptions,
    ImportResult,
    Policy,
)
from nextlabs_sdk.exceptions import NotFoundError

BASE_URL = "https://cloudaz.example.com"


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(
    data: object,
    status_code: int = 200,
    page_no: int = 0,
    page_size: int = 10,
    total_pages: int = 1,
    total_records: int = 1,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": page_no,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalNoOfRecords": total_records,
            "additionalAttributes": None,
        },
        request=_make_request(),
    )


def _make_policy_data() -> dict[str, Any]:
    return {
        "id": 82,
        "name": "Allow IT Ticket Access",
        "status": "DRAFT",
        "effectType": "allow",
        "tags": [],
        "subjectComponents": [],
        "toSubjectComponents": [],
        "actionComponents": [],
        "fromResourceComponents": [],
        "toResourceComponents": [],
        "allowObligations": [],
        "denyObligations": [],
        "subPolicyRefs": [],
        "attributes": [],
        "deploymentTime": 0,
        "deployed": False,
        "revisionCount": 0,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "lastUpdatedDate": 1713171640252,
        "authorities": [],
        "deploymentTargets": [],
    }


def test_get_returns_policy() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = _make_envelope(data=_make_policy_data())
    when(client).get("/console/api/v1/policy/mgmt/82").thenReturn(response)

    policy = service.get(82)

    assert isinstance(policy, Policy)
    assert policy.id == 82
    assert policy.name == "Allow IT Ticket Access"
    assert policy.effect_type == "allow"


def test_get_active_returns_policy() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = _make_envelope(data=_make_policy_data())
    when(client).get("/console/api/v1/policy/mgmt/active/82").thenReturn(response)

    policy = service.get_active(82)

    assert isinstance(policy, Policy)
    assert policy.id == 82


def test_create_returns_id() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    payload: dict[str, object] = {
        "name": "New Policy",
        "effectType": "allow",
        "status": "DRAFT",
    }
    response = _make_envelope(data=82)
    when(client).post(
        "/console/api/v1/policy/mgmt/add",
        json=payload,
    ).thenReturn(response)

    result = service.create(payload)

    assert result == 82


def test_create_sub_policy_returns_id() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    payload: dict[str, object] = {
        "name": "Sub Policy",
        "effectType": "deny",
        "parentId": 82,
    }
    response = _make_envelope(data=83)
    when(client).post(
        "/console/api/v1/policy/mgmt/addSubPolicy",
        json=payload,
    ).thenReturn(response)

    result = service.create_sub_policy(payload)

    assert result == 83


def test_modify_returns_id() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    payload: dict[str, object] = {
        "id": 82,
        "name": "Updated Policy",
        "effectType": "allow",
    }
    response = _make_envelope(data=82)
    when(client).put(
        "/console/api/v1/policy/mgmt/modify",
        json=payload,
    ).thenReturn(response)

    result = service.modify(payload)

    assert result == 82


def test_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).delete(
        "/console/api/v1/policy/mgmt/remove/82",
    ).thenReturn(response)

    service.delete(82)


def test_bulk_delete_succeeds() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/policy/mgmt/bulkDelete",
        json=[82, 83],
    ).thenReturn(response)

    service.bulk_delete([82, 83])


def test_bulk_delete_xacml_succeeds() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).request(
        "DELETE",
        "/console/api/v1/policy/mgmt/bulkDeleteXacmlPolicy",
        json=[82, 83],
    ).thenReturn(response)

    service.bulk_delete_xacml([82, 83])


def test_deploy_returns_results() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    deploy_requests: list[dict[str, object]] = [
        {"id": 82, "type": "POLICY", "push": True, "deploymentTime": -1},
    ]
    response_data = [
        {
            "id": 82,
            "pushResults": [
                {
                    "dpsUrl": "https://cc-prod-01:8443/dps",
                    "success": True,
                    "message": "Push Successful",
                },
            ],
        },
    ]
    response = _make_envelope(data=response_data)
    when(client).post(
        "/console/api/v1/policy/mgmt/deploy",
        json=deploy_requests,
    ).thenReturn(response)

    results = service.deploy(deploy_requests)

    assert len(results) == 1
    assert isinstance(results[0], DeploymentResult)
    assert results[0].id == 82
    assert results[0].push_results[0].success is True


def test_undeploy_succeeds() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = httpx.Response(200, request=_make_request())
    when(client).post(
        "/console/api/v1/policy/mgmt/unDeploy",
        json=[82, 83],
    ).thenReturn(response)

    service.undeploy([82, 83])


def test_find_dependencies_returns_list() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    dep_data = [
        {
            "id": 50,
            "type": "COMPONENT",
            "group": "RESOURCE",
            "name": "Security Vulnerabilities",
            "folderPath": None,
            "optional": False,
            "provided": True,
            "sub": False,
        },
        {
            "id": 90,
            "type": "POLICY",
            "group": None,
            "name": "Parent Policy",
        },
    ]
    response = _make_envelope(data=dep_data)
    when(client).post(
        "/console/api/v1/policy/mgmt/findDependencies",
        json=[82],
    ).thenReturn(response)

    deps = service.find_dependencies([82])

    assert len(deps) == 2
    assert isinstance(deps[0], Dependency)
    assert deps[0].group == "RESOURCE"
    assert deps[1].group is None
    assert deps[1].type == "POLICY"


def test_export_returns_filename() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    response = _make_envelope(data="export_2024.bin")
    when(client).post(
        "/console/api/v1/policy/mgmt/export",
        json=entities,
        params={"exportMode": "PLAIN"},
    ).thenReturn(response)

    result = service.export(entities)

    assert result == "export_2024.bin"


def test_export_with_sande_mode() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    response = _make_envelope(data="export_enc.bin")
    when(client).post(
        "/console/api/v1/policy/mgmt/export",
        json=entities,
        params={"exportMode": "SANDE"},
    ).thenReturn(response)

    result = service.export(entities, export_mode="SANDE")

    assert result == "export_enc.bin"


def test_export_all_returns_filename() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = _make_envelope(data="export_all_2024.bin")
    when(client).get(
        "/console/api/v1/policy/mgmt/exportAll",
        params={"exportMode": "PLAIN"},
    ).thenReturn(response)

    result = service.export_all()

    assert result == "export_all_2024.bin"


def test_export_options_returns_model() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = _make_envelope(
        data={"sandeEnabled": True, "plainTextEnabled": True},
    )
    when(client).get(
        "/console/api/v1/policy/mgmt/exportOptions",
    ).thenReturn(response)

    opts = service.export_options()

    assert isinstance(opts, ExportOptions)
    assert opts.sande_enabled is True
    assert opts.plain_text_enabled is True


def test_generate_xacml_returns_filename() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    response = _make_envelope(data="policies.xacml")
    when(client).post(
        "/console/api/v1/policy/mgmt/generateXACML",
        json=entities,
    ).thenReturn(response)

    result = service.generate_xacml(entities)

    assert result == "policies.xacml"


def test_generate_pdf_returns_filename() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    response = _make_envelope(data="policies.pdf")
    when(client).post(
        "/console/api/v1/policy/mgmt/generatePDF",
        json=entities,
    ).thenReturn(response)

    result = service.generate_pdf(entities)

    assert result == "policies.pdf"


def test_import_policies_returns_result() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    files: dict[str, tuple[str, bytes, str]] = {
        "policyFiles": ("export.bin", b"binary-data", "application/octet-stream"),
    }
    import_data: dict[str, Any] = {
        "total_components": 5,
        "total_policies": 3,
        "total_policy_models": 2,
        "non_blocking_error": False,
    }
    response = _make_envelope(data=import_data)
    when(client).post(
        "/console/api/v1/policy/mgmt/import",
        files=files,
        params={"importMechanism": "PARTIAL", "cleanup": "false"},
    ).thenReturn(response)

    result = service.import_policies(files)

    assert isinstance(result, ImportResult)
    assert result.total_policies == 3
    assert result.total_components == 5


def test_import_policies_with_overwrite() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    files: dict[str, tuple[str, bytes, str]] = {
        "policyFiles": ("export.bin", b"data", "application/octet-stream"),
    }
    import_data: dict[str, Any] = {
        "total_components": 1,
        "total_policies": 1,
        "total_policy_models": 1,
        "non_blocking_error": True,
    }
    response = _make_envelope(data=import_data)
    when(client).post(
        "/console/api/v1/policy/mgmt/import",
        files=files,
        params={"importMechanism": "OVERWRITE", "cleanup": "true"},
    ).thenReturn(response)

    result = service.import_policies(
        files,
        import_mechanism="OVERWRITE",
        cleanup=True,
    )

    assert result.non_blocking_error is True


def test_import_xacml_returns_result() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    file_tuple = ("policy.xacml", b"<Policy/>", "application/xml")
    import_data: dict[str, Any] = {
        "total_components": 0,
        "total_policies": 1,
        "total_policy_models": 0,
        "non_blocking_error": False,
    }
    response = _make_envelope(data=import_data)
    when(client).post(
        "/console/api/v1/policy/mgmt/importXacmlPolicy",
        files={"file": file_tuple},
    ).thenReturn(response)

    result = service.import_xacml(file_tuple)

    assert isinstance(result, ImportResult)
    assert result.total_policies == 1


def test_validate_obligations_succeeds() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    payload: dict[str, object] = {"policyId": 82, "obligations": []}
    response = httpx.Response(200, request=_make_request())
    when(client).post(
        "/console/api/v1/policy/mgmt/obligation/daeValidate",
        json=payload,
    ).thenReturn(response)

    service.validate_obligations(payload)


def test_get_raises_not_found() -> None:
    client = mock(httpx.Client)
    service = PolicyService(client)
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    when(client).get("/console/api/v1/policy/mgmt/999").thenReturn(response)

    with pytest.raises(NotFoundError):
        service.get(999)
