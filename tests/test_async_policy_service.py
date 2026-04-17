from __future__ import annotations

import asyncio
from typing import Any, Awaitable, TypeVar

import httpx
import pytest
from mockito import mock, when

from nextlabs_sdk._cloudaz._component_models import (
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._policies import AsyncPolicyService
from nextlabs_sdk._cloudaz._policy_models import (
    ExportOptions,
    ImportResult,
    Policy,
)
from nextlabs_sdk.exceptions import NotFoundError

BASE_URL = "https://cloudaz.example.com"
MGMT = "/console/api/v1/policy/mgmt"
EXPORT_URL = f"{MGMT}/export"
IMPORT_URL = f"{MGMT}/import"
RETRIEVE_ALL_URL = f"{MGMT}/retrieveAllPolicies"

T = TypeVar("T")


def _make_request(path: str = "/api") -> httpx.Request:
    return httpx.Request("GET", f"{BASE_URL}{path}")


def _make_envelope(data: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "statusCode": "1003",
            "message": "Data found successfully",
            "data": data,
            "pageNo": 0,
            "pageSize": 10,
            "totalPages": 1,
            "totalNoOfRecords": 1,
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


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)  # type: ignore[arg-type]


@pytest.fixture
def client_and_service() -> tuple[Any, AsyncPolicyService]:
    client = mock(httpx.AsyncClient)
    return client, AsyncPolicyService(client)


@pytest.mark.parametrize(
    "method_name,url",
    [
        pytest.param("get", f"{MGMT}/82", id="get"),
        pytest.param("get_active", f"{MGMT}/active/82", id="get_active"),
    ],
)
def test_async_get_variants_return_policy(client_and_service, method_name, url):
    client, service = client_and_service
    when(client).get(url).thenReturn(_make_envelope(data=_make_policy_data()))

    policy: Policy = _run(getattr(service, method_name)(82))
    assert policy.id == 82


def test_async_get_returns_policy_name(client_and_service):
    client, service = client_and_service
    when(client).get(f"{MGMT}/82").thenReturn(_make_envelope(data=_make_policy_data()))

    policy = _run(service.get(82))
    assert policy.name == "Allow IT Ticket Access"


@pytest.mark.parametrize(
    "method_name,endpoint,payload,expected_id",
    [
        pytest.param(
            "create",
            "add",
            {"name": "New", "effectType": "allow", "status": "DRAFT"},
            82,
            id="create",
        ),
        pytest.param(
            "create_sub_policy",
            "addSubPolicy",
            {"name": "Sub", "effectType": "deny", "parentId": 82},
            83,
            id="create_sub_policy",
        ),
    ],
)
def test_async_create_endpoints_return_id(
    client_and_service,
    method_name,
    endpoint,
    payload,
    expected_id,
):
    client, service = client_and_service
    when(client).post(
        f"{MGMT}/{endpoint}",
        json=payload,
    ).thenReturn(_make_envelope(data=expected_id))

    assert _run(getattr(service, method_name)(payload)) == expected_id


def test_async_modify_returns_id(client_and_service):
    client, service = client_and_service
    payload: dict[str, object] = {"id": 82, "name": "Updated", "effectType": "allow"}
    when(client).put(
        f"{MGMT}/modify",
        json=payload,
    ).thenReturn(_make_envelope(data=82))

    assert _run(service.modify(payload)) == 82


def test_async_delete_succeeds(client_and_service):
    client, service = client_and_service
    when(client).delete(f"{MGMT}/remove/82").thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    _run(service.delete(82))


@pytest.mark.parametrize(
    "method_name,endpoint",
    [
        pytest.param("bulk_delete", "bulkDelete", id="bulk_delete"),
        pytest.param(
            "bulk_delete_xacml",
            "bulkDeleteXacmlPolicy",
            id="bulk_delete_xacml",
        ),
    ],
)
def test_async_bulk_delete_variants(client_and_service, method_name, endpoint):
    client, service = client_and_service
    when(client).request(
        "DELETE",
        f"{MGMT}/{endpoint}",
        json=[82, 83],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(getattr(service, method_name)([82, 83]))


def test_async_deploy_returns_results(client_and_service):
    client, service = client_and_service
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
    when(client).post(
        f"{MGMT}/deploy",
        json=deploy_requests,
    ).thenReturn(_make_envelope(data=response_data))

    results: list[DeploymentResult] = _run(service.deploy(deploy_requests))
    assert len(results) == 1
    assert results[0].push_results[0].success is True


def test_async_undeploy_succeeds(client_and_service):
    client, service = client_and_service
    when(client).post(
        f"{MGMT}/unDeploy",
        json=[82],
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.undeploy([82]))


def test_async_find_dependencies_returns_list(client_and_service):
    client, service = client_and_service
    dep_data = [
        {
            "id": 50,
            "type": "COMPONENT",
            "group": "RESOURCE",
            "name": "Security Vulnerabilities",
        },
    ]
    when(client).post(
        f"{MGMT}/findDependencies",
        json=[82],
    ).thenReturn(_make_envelope(data=dep_data))

    deps: list[Dependency] = _run(service.find_dependencies([82]))
    assert len(deps) == 1
    assert deps[0].name == "Security Vulnerabilities"


@pytest.mark.parametrize(
    "export_mode,kwargs,filename",
    [
        pytest.param("PLAIN", {}, "export_2024.bin", id="default-plain"),
        pytest.param(
            "SANDE",
            {"export_mode": "SANDE"},
            "export_enc.bin",
            id="sande-mode",
        ),
    ],
)
def test_async_export_returns_filename(
    client_and_service,
    export_mode,
    kwargs,
    filename,
):
    client, service = client_and_service
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    when(client).post(
        EXPORT_URL,
        json=entities,
        params={"exportMode": export_mode},
    ).thenReturn(_make_envelope(data=filename))

    assert _run(service.export(entities, **kwargs)) == filename


def test_async_export_all_returns_filename(client_and_service):
    client, service = client_and_service
    when(client).get(
        f"{MGMT}/exportAll",
        params={"exportMode": "PLAIN"},
    ).thenReturn(_make_envelope(data="export_all.bin"))

    assert _run(service.export_all()) == "export_all.bin"


def test_async_export_options_returns_model(client_and_service):
    client, service = client_and_service
    when(client).get(f"{MGMT}/exportOptions").thenReturn(
        _make_envelope(data={"sandeEnabled": True, "plainTextEnabled": True}),
    )

    opts: ExportOptions = _run(service.export_options())
    assert opts.sande_enabled is True


@pytest.mark.parametrize(
    "method_name,endpoint,filename",
    [
        pytest.param("generate_xacml", "generateXACML", "policies.xacml", id="xacml"),
        pytest.param("generate_pdf", "generatePDF", "policies.pdf", id="pdf"),
    ],
)
def test_async_generate_variants_return_filename(
    client_and_service,
    method_name,
    endpoint,
    filename,
):
    client, service = client_and_service
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    when(client).post(
        f"{MGMT}/{endpoint}",
        json=entities,
    ).thenReturn(_make_envelope(data=filename))

    assert _run(getattr(service, method_name)(entities)) == filename


@pytest.mark.parametrize(
    "kwargs,params,non_blocking",
    [
        pytest.param(
            {},
            {"importMechanism": "PARTIAL", "cleanup": "false"},
            False,
            id="partial",
        ),
        pytest.param(
            {"import_mechanism": "OVERWRITE", "cleanup": True},
            {"importMechanism": "OVERWRITE", "cleanup": "true"},
            True,
            id="overwrite-cleanup",
        ),
    ],
)
def test_async_import_policies_returns_result(
    client_and_service,
    kwargs,
    params,
    non_blocking,
):
    client, service = client_and_service
    files: dict[str, tuple[str, bytes, str]] = {
        "policyFiles": ("export.bin", b"binary-data", "application/octet-stream"),
    }
    import_data: dict[str, Any] = {
        "total_components": 5,
        "total_policies": 3,
        "total_policy_models": 2,
        "non_blocking_error": non_blocking,
    }
    when(client).post(
        IMPORT_URL,
        files=files,
        params=params,
    ).thenReturn(_make_envelope(data=import_data))

    result: ImportResult = _run(service.import_policies(files, **kwargs))
    assert result.total_policies == 3
    assert result.non_blocking_error is non_blocking


def test_async_import_xacml_returns_result(client_and_service):
    client, service = client_and_service
    file_tuple = ("policy.xacml", b"<Policy/>", "application/xml")
    import_data: dict[str, Any] = {
        "total_components": 0,
        "total_policies": 1,
        "total_policy_models": 0,
        "non_blocking_error": False,
    }
    when(client).post(
        f"{MGMT}/importXacmlPolicy",
        files={"file": file_tuple},
    ).thenReturn(_make_envelope(data=import_data))

    result: ImportResult = _run(service.import_xacml(file_tuple))
    assert result.total_policies == 1


def test_async_validate_obligations_succeeds(client_and_service):
    client, service = client_and_service
    payload: dict[str, object] = {"policyId": 82, "obligations": []}
    when(client).post(
        f"{MGMT}/obligation/daeValidate",
        json=payload,
    ).thenReturn(httpx.Response(200, request=_make_request()))

    _run(service.validate_obligations(payload))


def test_async_get_raises_not_found(client_and_service):
    client, service = client_and_service
    response = httpx.Response(
        404,
        json={"message": "Not found"},
        request=_make_request(),
    )
    when(client).get(f"{MGMT}/999").thenReturn(response)

    with pytest.raises(NotFoundError):
        _run(service.get(999))


@pytest.mark.parametrize(
    "export_mode,kwargs,filename",
    [
        pytest.param(
            "PLAIN",
            {},
            "Policy_Export_ASYNC.bin",
            id="default-plain",
        ),
        pytest.param(
            "SANDE",
            {"export_mode": "SANDE"},
            "Policy_Export_SANDE.bin",
            id="sande-mode",
        ),
    ],
)
def test_async_retrieve_all_policies_returns_filename(
    client_and_service,
    export_mode,
    kwargs,
    filename,
):
    client, service = client_and_service
    when(client).get(
        RETRIEVE_ALL_URL,
        params={"exportMode": export_mode},
    ).thenReturn(_make_envelope(data=filename))

    assert _run(service.retrieve_all_policies(**kwargs)) == filename
