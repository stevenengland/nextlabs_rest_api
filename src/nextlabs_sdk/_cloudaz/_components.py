from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._component_models import (
    Component,
    Dependency,
    DeploymentResult,
)
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk.exceptions import raise_for_status


class ComponentService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self, component_id: int) -> Component:
        response = self._client.get(
            f"/console/api/v1/component/mgmt/{component_id}",
        )
        return Component.model_validate(parse_data(response))

    def get_active(self, component_id: int) -> Component:
        response = self._client.get(
            f"/console/api/v1/component/mgmt/active/{component_id}",
        )
        return Component.model_validate(parse_data(response))

    def create(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/component/mgmt/add",
            json=payload,
        )
        return parse_data(response)

    def create_sub_component(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/component/mgmt/addSubComponent",
            json=payload,
        )
        return parse_data(response)

    def modify(self, payload: dict[str, object]) -> int:
        response = self._client.put(
            "/console/api/v1/component/mgmt/modify",
            json=payload,
        )
        return parse_data(response)

    def delete(self, component_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/component/mgmt/remove/{component_id}",
        )
        raise_for_status(response)

    def bulk_delete(self, component_ids: list[int]) -> None:
        response = self._client.request(
            "DELETE",
            "/console/api/v1/component/mgmt/bulkDelete",
            json=component_ids,
        )
        raise_for_status(response)

    def deploy(
        self,
        requests: list[dict[str, object]],
    ) -> list[DeploymentResult]:
        response = self._client.post(
            "/console/api/v1/component/mgmt/deploy",
            json=requests,
        )
        raw = parse_data(response)
        return [DeploymentResult.model_validate(entry) for entry in raw]

    def undeploy(self, component_ids: list[int]) -> None:
        response = self._client.post(
            "/console/api/v1/component/mgmt/unDeploy",
            json=component_ids,
        )
        raise_for_status(response)

    def find_dependencies(
        self,
        component_ids: list[int],
    ) -> list[Dependency]:
        response = self._client.post(
            "/console/api/v1/component/mgmt/findDependencies",
            json=component_ids,
        )
        raw = parse_data(response)
        return [Dependency.model_validate(entry) for entry in raw]


class AsyncComponentService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get(self, component_id: int) -> Component:
        resp = await self._client.get(
            f"/console/api/v1/component/mgmt/{component_id}",
        )
        return Component.model_validate(parse_data(resp))

    async def get_active(self, component_id: int) -> Component:
        resp = await self._client.get(
            f"/console/api/v1/component/mgmt/active/{component_id}",
        )
        return Component.model_validate(parse_data(resp))

    async def create(self, payload: dict[str, object]) -> int:
        resp = await self._client.post(
            "/console/api/v1/component/mgmt/add",
            json=payload,
        )
        return parse_data(resp)

    async def create_sub_component(self, payload: dict[str, object]) -> int:
        resp = await self._client.post(
            "/console/api/v1/component/mgmt/addSubComponent",
            json=payload,
        )
        return parse_data(resp)

    async def modify(self, payload: dict[str, object]) -> int:
        resp = await self._client.put(
            "/console/api/v1/component/mgmt/modify",
            json=payload,
        )
        return parse_data(resp)

    async def delete(self, component_id: int) -> None:
        resp = await self._client.delete(
            f"/console/api/v1/component/mgmt/remove/{component_id}",
        )
        raise_for_status(resp)

    async def bulk_delete(self, component_ids: list[int]) -> None:
        resp = await self._client.request(
            "DELETE",
            "/console/api/v1/component/mgmt/bulkDelete",
            json=component_ids,
        )
        raise_for_status(resp)

    async def deploy(
        self,
        requests: list[dict[str, object]],
    ) -> list[DeploymentResult]:
        resp = await self._client.post(
            "/console/api/v1/component/mgmt/deploy",
            json=requests,
        )
        raw = parse_data(resp)
        return [DeploymentResult.model_validate(entry) for entry in raw]

    async def undeploy(self, component_ids: list[int]) -> None:
        resp = await self._client.post(
            "/console/api/v1/component/mgmt/unDeploy",
            json=component_ids,
        )
        raise_for_status(resp)

    async def find_dependencies(
        self,
        component_ids: list[int],
    ) -> list[Dependency]:
        resp = await self._client.post(
            "/console/api/v1/component/mgmt/findDependencies",
            json=component_ids,
        )
        raw = parse_data(resp)
        return [Dependency.model_validate(entry) for entry in raw]
