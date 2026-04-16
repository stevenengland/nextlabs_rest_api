from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._component_models import (
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._policy_models import (
    ExportOptions,
    ImportResult,
    Policy,
)
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk.exceptions import raise_for_status


class PolicyService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self, policy_id: int) -> Policy:
        response = self._client.get(
            f"/console/api/v1/policy/mgmt/{policy_id}",
        )
        return Policy.model_validate(parse_data(response))

    def get_active(self, policy_id: int) -> Policy:
        response = self._client.get(
            f"/console/api/v1/policy/mgmt/active/{policy_id}",
        )
        return Policy.model_validate(parse_data(response))

    def create(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/add",
            json=payload,
        )
        return parse_data(response)

    def create_sub_policy(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/addSubPolicy",
            json=payload,
        )
        return parse_data(response)

    def modify(self, payload: dict[str, object]) -> int:
        response = self._client.put(
            "/console/api/v1/policy/mgmt/modify",
            json=payload,
        )
        return parse_data(response)

    def delete(self, policy_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/policy/mgmt/remove/{policy_id}",
        )
        raise_for_status(response)

    def bulk_delete(self, policy_ids: list[int]) -> None:
        response = self._client.request(
            "DELETE",
            "/console/api/v1/policy/mgmt/bulkDelete",
            json=policy_ids,
        )
        raise_for_status(response)

    def bulk_delete_xacml(self, policy_ids: list[int]) -> None:
        response = self._client.request(
            "DELETE",
            "/console/api/v1/policy/mgmt/bulkDeleteXacmlPolicy",
            json=policy_ids,
        )
        raise_for_status(response)

    def deploy(
        self,
        requests: list[dict[str, object]],
    ) -> list[DeploymentResult]:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/deploy",
            json=requests,
        )
        raw = parse_data(response)
        return [DeploymentResult.model_validate(entry) for entry in raw]

    def undeploy(self, policy_ids: list[int]) -> None:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/unDeploy",
            json=policy_ids,
        )
        raise_for_status(response)

    def find_dependencies(
        self,
        policy_ids: list[int],
    ) -> list[Dependency]:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/findDependencies",
            json=policy_ids,
        )
        raw = parse_data(response)
        return [Dependency.model_validate(entry) for entry in raw]

    def export(
        self,
        entities: list[dict[str, object]],
        *,
        export_mode: str = "PLAIN",
    ) -> str:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/export",
            json=entities,
            params={"exportMode": export_mode},
        )
        return parse_data(response)

    def export_all(self, *, export_mode: str = "PLAIN") -> str:
        response = self._client.get(
            "/console/api/v1/policy/mgmt/exportAll",
            params={"exportMode": export_mode},
        )
        return parse_data(response)

    def export_options(self) -> ExportOptions:
        response = self._client.get(
            "/console/api/v1/policy/mgmt/exportOptions",
        )
        return ExportOptions.model_validate(parse_data(response))

    def generate_xacml(
        self,
        entities: list[dict[str, object]],
    ) -> str:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/generateXACML",
            json=entities,
        )
        return parse_data(response)

    def generate_pdf(
        self,
        entities: list[dict[str, object]],
    ) -> str:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/generatePDF",
            json=entities,
        )
        return parse_data(response)

    def import_policies(
        self,
        files: dict[str, tuple[str, bytes, str]],
        *,
        import_mechanism: str = "PARTIAL",
        cleanup: bool = False,
    ) -> ImportResult:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/import",
            files=files,
            params={
                "importMechanism": import_mechanism,
                "cleanup": str(cleanup).lower(),
            },
        )
        return ImportResult.model_validate(parse_data(response))

    def import_xacml(
        self,
        file: tuple[str, bytes, str],
    ) -> ImportResult:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/importXacmlPolicy",
            files={"file": file},
        )
        return ImportResult.model_validate(parse_data(response))

    def validate_obligations(
        self,
        payload: dict[str, object],
    ) -> None:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/obligation/daeValidate",
            json=payload,
        )
        raise_for_status(response)
