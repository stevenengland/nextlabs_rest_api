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

_DELETE_METHOD = "DELETE"
_PLAIN_MODE = "PLAIN"
_EXPORT_MODE_PARAM = "exportMode"


class PolicyService:  # noqa: WPS214

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self, policy_id: int) -> Policy:
        response = self._client.get(
            f"/console/api/v1/policy/mgmt/{policy_id}",
        )
        return Policy.model_validate(parse_data(response))  # noqa: WPS204

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
            _DELETE_METHOD,
            "/console/api/v1/policy/mgmt/bulkDelete",
            json=policy_ids,
        )
        raise_for_status(response)

    def bulk_delete_xacml(self, policy_ids: list[int]) -> None:
        response = self._client.request(
            _DELETE_METHOD,
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
        export_mode: str = _PLAIN_MODE,
    ) -> str:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/export",
            json=entities,
            params={_EXPORT_MODE_PARAM: export_mode},
        )
        return parse_data(response)

    def export_all(self, *, export_mode: str = _PLAIN_MODE) -> str:
        response = self._client.get(
            "/console/api/v1/policy/mgmt/exportAll",
            params={_EXPORT_MODE_PARAM: export_mode},
        )
        return parse_data(response)

    def retrieve_all_policies(self, *, export_mode: str = _PLAIN_MODE) -> str:
        response = self._client.get(
            "/console/api/v1/policy/mgmt/retrieveAllPolicies",
            params={_EXPORT_MODE_PARAM: export_mode},
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
        policy_file: tuple[str, bytes, str],
    ) -> ImportResult:
        response = self._client.post(
            "/console/api/v1/policy/mgmt/importXacmlPolicy",
            files={"file": policy_file},
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


class AsyncPolicyService:  # noqa: WPS214

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get(self, policy_id: int) -> Policy:
        resp = await self._client.get(
            f"/console/api/v1/policy/mgmt/{policy_id}",
        )
        return Policy.model_validate(parse_data(resp))  # noqa: WPS204

    async def get_active(self, policy_id: int) -> Policy:
        resp = await self._client.get(
            f"/console/api/v1/policy/mgmt/active/{policy_id}",
        )
        return Policy.model_validate(parse_data(resp))

    async def create(self, payload: dict[str, object]) -> int:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/add",
            json=payload,
        )
        return parse_data(resp)

    async def create_sub_policy(self, payload: dict[str, object]) -> int:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/addSubPolicy",
            json=payload,
        )
        return parse_data(resp)

    async def modify(self, payload: dict[str, object]) -> int:
        resp = await self._client.put(
            "/console/api/v1/policy/mgmt/modify",
            json=payload,
        )
        return parse_data(resp)

    async def delete(self, policy_id: int) -> None:
        resp = await self._client.delete(
            f"/console/api/v1/policy/mgmt/remove/{policy_id}",
        )
        raise_for_status(resp)

    async def bulk_delete(self, policy_ids: list[int]) -> None:
        resp = await self._client.request(
            _DELETE_METHOD,
            "/console/api/v1/policy/mgmt/bulkDelete",
            json=policy_ids,
        )
        raise_for_status(resp)

    async def bulk_delete_xacml(self, policy_ids: list[int]) -> None:
        resp = await self._client.request(
            _DELETE_METHOD,
            "/console/api/v1/policy/mgmt/bulkDeleteXacmlPolicy",
            json=policy_ids,
        )
        raise_for_status(resp)

    async def deploy(
        self,
        requests: list[dict[str, object]],
    ) -> list[DeploymentResult]:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/deploy",
            json=requests,
        )
        raw = parse_data(resp)
        return [DeploymentResult.model_validate(entry) for entry in raw]

    async def undeploy(self, policy_ids: list[int]) -> None:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/unDeploy",
            json=policy_ids,
        )
        raise_for_status(resp)

    async def find_dependencies(
        self,
        policy_ids: list[int],
    ) -> list[Dependency]:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/findDependencies",
            json=policy_ids,
        )
        raw = parse_data(resp)
        return [Dependency.model_validate(entry) for entry in raw]

    async def export(
        self,
        entities: list[dict[str, object]],
        *,
        export_mode: str = _PLAIN_MODE,
    ) -> str:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/export",
            json=entities,
            params={_EXPORT_MODE_PARAM: export_mode},
        )
        return parse_data(resp)

    async def export_all(self, *, export_mode: str = _PLAIN_MODE) -> str:
        resp = await self._client.get(
            "/console/api/v1/policy/mgmt/exportAll",
            params={_EXPORT_MODE_PARAM: export_mode},
        )
        return parse_data(resp)

    async def retrieve_all_policies(self, *, export_mode: str = _PLAIN_MODE) -> str:
        resp = await self._client.get(
            "/console/api/v1/policy/mgmt/retrieveAllPolicies",
            params={_EXPORT_MODE_PARAM: export_mode},
        )
        return parse_data(resp)

    async def export_options(self) -> ExportOptions:
        resp = await self._client.get(
            "/console/api/v1/policy/mgmt/exportOptions",
        )
        return ExportOptions.model_validate(parse_data(resp))

    async def generate_xacml(
        self,
        entities: list[dict[str, object]],
    ) -> str:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/generateXACML",
            json=entities,
        )
        return parse_data(resp)

    async def generate_pdf(
        self,
        entities: list[dict[str, object]],
    ) -> str:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/generatePDF",
            json=entities,
        )
        return parse_data(resp)

    async def import_policies(
        self,
        files: dict[str, tuple[str, bytes, str]],
        *,
        import_mechanism: str = "PARTIAL",
        cleanup: bool = False,
    ) -> ImportResult:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/import",
            files=files,
            params={
                "importMechanism": import_mechanism,
                "cleanup": str(cleanup).lower(),
            },
        )
        return ImportResult.model_validate(parse_data(resp))

    async def import_xacml(
        self,
        policy_file: tuple[str, bytes, str],
    ) -> ImportResult:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/importXacmlPolicy",
            files={"file": policy_file},
        )
        return ImportResult.model_validate(parse_data(resp))

    async def validate_obligations(
        self,
        payload: dict[str, object],
    ) -> None:
        resp = await self._client.post(
            "/console/api/v1/policy/mgmt/obligation/daeValidate",
            json=payload,
        )
        raise_for_status(resp)
