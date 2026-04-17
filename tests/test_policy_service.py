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
MGMT = "/console/api/v1/policy/mgmt"


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


@pytest.fixture
def client_service() -> tuple[Any, PolicyService]:
    client = mock(httpx.Client)
    return client, PolicyService(client)


@pytest.mark.parametrize(
    "path,invoke",
    [
        pytest.param(f"{MGMT}/82", lambda svc: svc.get(82), id="get"),
        pytest.param(
            f"{MGMT}/active/82", lambda svc: svc.get_active(82), id="get-active"
        ),
    ],
)
def test_get_returns_policy(
    client_service: tuple[Any, PolicyService],
    path: str,
    invoke: Any,
):
    client, service = client_service
    when(client).get(path).thenReturn(_make_envelope(data=_make_policy_data()))

    policy = invoke(service)

    assert isinstance(policy, Policy)
    assert policy.id == 82
    assert policy.name == "Allow IT Ticket Access"
    assert policy.effect_type == "allow"


@pytest.mark.parametrize(
    "path,invoke,payload,expected_id",
    [
        pytest.param(
            f"{MGMT}/add",
            lambda svc, p: svc.create(p),
            {"name": "New Policy", "effectType": "allow", "status": "DRAFT"},
            82,
            id="create",
        ),
        pytest.param(
            f"{MGMT}/addSubPolicy",
            lambda svc, p: svc.create_sub_policy(p),
            {"name": "Sub Policy", "effectType": "deny", "parentId": 82},
            83,
            id="create-sub-policy",
        ),
    ],
)
def test_create_policy_returns_id(
    client_service: tuple[Any, PolicyService],
    path: str,
    invoke: Any,
    payload: dict[str, object],
    expected_id: int,
):
    client, service = client_service
    when(client).post(path, json=payload).thenReturn(_make_envelope(data=expected_id))

    assert invoke(service, payload) == expected_id


def test_modify_returns_id(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    payload: dict[str, object] = {
        "id": 82,
        "name": "Updated Policy",
        "effectType": "allow",
    }
    when(client).put(f"{MGMT}/modify", json=payload).thenReturn(_make_envelope(data=82))

    assert service.modify(payload) == 82


def test_delete_succeeds(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    when(client).delete(f"{MGMT}/remove/82").thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    service.delete(82)


@pytest.mark.parametrize(
    "path,invoke",
    [
        pytest.param(
            f"{MGMT}/bulkDelete",
            lambda svc: svc.bulk_delete([82, 83]),
            id="bulk-delete",
        ),
        pytest.param(
            f"{MGMT}/bulkDeleteXacmlPolicy",
            lambda svc: svc.bulk_delete_xacml([82, 83]),
            id="bulk-delete-xacml",
        ),
    ],
)
def test_bulk_delete_variants(
    client_service: tuple[Any, PolicyService],
    path: str,
    invoke: Any,
):
    client, service = client_service
    when(client).request("DELETE", path, json=[82, 83]).thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    invoke(service)


def test_deploy_returns_results(client_service: tuple[Any, PolicyService]):
    client, service = client_service
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
    when(client).post(f"{MGMT}/deploy", json=deploy_requests).thenReturn(
        _make_envelope(data=response_data),
    )

    results = service.deploy(deploy_requests)

    assert len(results) == 1
    assert isinstance(results[0], DeploymentResult)
    assert results[0].id == 82
    assert results[0].push_results[0].success is True


def test_undeploy_succeeds(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    when(client).post(f"{MGMT}/unDeploy", json=[82, 83]).thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    service.undeploy([82, 83])


def test_find_dependencies_returns_list(client_service: tuple[Any, PolicyService]):
    client, service = client_service
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
        {"id": 90, "type": "POLICY", "group": None, "name": "Parent Policy"},
    ]
    when(client).post(f"{MGMT}/findDependencies", json=[82]).thenReturn(
        _make_envelope(data=dep_data),
    )

    deps = service.find_dependencies([82])

    assert len(deps) == 2
    assert isinstance(deps[0], Dependency)
    assert deps[0].group == "RESOURCE"
    assert deps[1].group is None
    assert deps[1].type == "POLICY"


@pytest.mark.parametrize(
    "export_mode,expected_file",
    [
        pytest.param("PLAIN", "export_2024.bin", id="plain"),
        pytest.param("SANDE", "export_enc.bin", id="sande"),
    ],
)
def test_export_returns_filename(
    client_service: tuple[Any, PolicyService],
    export_mode: str,
    expected_file: str,
):
    client, service = client_service
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    when(client).post(
        f"{MGMT}/export",
        json=entities,
        params={"exportMode": export_mode},
    ).thenReturn(_make_envelope(data=expected_file))

    if export_mode == "PLAIN":
        assert service.export(entities) == expected_file
    else:
        assert service.export(entities, export_mode=export_mode) == expected_file


def test_export_all_returns_filename(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    when(client).get(
        f"{MGMT}/exportAll",
        params={"exportMode": "PLAIN"},
    ).thenReturn(_make_envelope(data="export_all_2024.bin"))

    assert service.export_all() == "export_all_2024.bin"


def test_export_options_returns_model(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    when(client).get(f"{MGMT}/exportOptions").thenReturn(
        _make_envelope(data={"sandeEnabled": True, "plainTextEnabled": True}),
    )

    opts = service.export_options()

    assert isinstance(opts, ExportOptions)
    assert opts.sande_enabled is True
    assert opts.plain_text_enabled is True


@pytest.mark.parametrize(
    "path,invoke,expected",
    [
        pytest.param(
            f"{MGMT}/generateXACML",
            lambda svc, entities: svc.generate_xacml(entities),
            "policies.xacml",
            id="generate-xacml",
        ),
        pytest.param(
            f"{MGMT}/generatePDF",
            lambda svc, entities: svc.generate_pdf(entities),
            "policies.pdf",
            id="generate-pdf",
        ),
    ],
)
def test_generate_returns_filename(
    client_service: tuple[Any, PolicyService],
    path: str,
    invoke: Any,
    expected: str,
):
    client, service = client_service
    entities: list[dict[str, object]] = [{"entityType": "POLICY", "id": 82}]
    when(client).post(path, json=entities).thenReturn(_make_envelope(data=expected))

    assert invoke(service, entities) == expected


@pytest.mark.parametrize(
    "kwargs,params,non_blocking",
    [
        pytest.param(
            {},
            {"importMechanism": "PARTIAL", "cleanup": "false"},
            False,
            id="default-partial",
        ),
        pytest.param(
            {"import_mechanism": "OVERWRITE", "cleanup": True},
            {"importMechanism": "OVERWRITE", "cleanup": "true"},
            True,
            id="overwrite-with-cleanup",
        ),
    ],
)
def test_import_policies_returns_result(
    client_service: tuple[Any, PolicyService],
    kwargs: dict[str, Any],
    params: dict[str, str],
    non_blocking: bool,
):
    client, service = client_service
    files: dict[str, tuple[str, bytes, str]] = {
        "policyFiles": ("export.bin", b"binary-data", "application/octet-stream"),
    }
    import_data: dict[str, Any] = {
        "total_components": 5,
        "total_policies": 3,
        "total_policy_models": 2,
        "non_blocking_error": non_blocking,
    }
    when(client).post(f"{MGMT}/import", files=files, params=params).thenReturn(
        _make_envelope(data=import_data),
    )

    result = service.import_policies(files, **kwargs)

    assert isinstance(result, ImportResult)
    assert result.total_policies == 3
    assert result.total_components == 5
    assert result.non_blocking_error is non_blocking


def test_import_xacml_returns_result(client_service: tuple[Any, PolicyService]):
    client, service = client_service
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

    result = service.import_xacml(file_tuple)

    assert isinstance(result, ImportResult)
    assert result.total_policies == 1


def test_validate_obligations_succeeds(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    payload: dict[str, object] = {"policyId": 82, "obligations": []}
    when(client).post(f"{MGMT}/obligation/daeValidate", json=payload).thenReturn(
        httpx.Response(200, request=_make_request()),
    )

    service.validate_obligations(payload)


def test_get_raises_not_found(client_service: tuple[Any, PolicyService]):
    client, service = client_service
    when(client).get(f"{MGMT}/999").thenReturn(
        httpx.Response(404, json={"message": "Not found"}, request=_make_request()),
    )

    with pytest.raises(NotFoundError):
        service.get(999)


@pytest.mark.parametrize(
    "kwargs,export_mode,expected",
    [
        pytest.param({}, "PLAIN", "Policy_Export_20260417.bin", id="default-plain"),
        pytest.param(
            {"export_mode": "SANDE"}, "SANDE", "Policy_Export_SANDE.bin", id="sande"
        ),
    ],
)
def test_retrieve_all_policies_returns_filename(
    client_service: tuple[Any, PolicyService],
    kwargs: dict[str, str],
    export_mode: str,
    expected: str,
):
    client, service = client_service
    when(client).get(
        f"{MGMT}/retrieveAllPolicies",
        params={"exportMode": export_mode},
    ).thenReturn(_make_envelope(data=expected))

    assert service.retrieve_all_policies(**kwargs) == expected
