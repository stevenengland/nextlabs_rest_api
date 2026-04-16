from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._component_type_models import (
    AttributeConfig,
    ComponentType,
)
from nextlabs_sdk._cloudaz._response import parse_data
from nextlabs_sdk.exceptions import raise_for_status


class ComponentTypeService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def get(self, component_type_id: int) -> ComponentType:
        response = self._client.get(
            f"/console/api/v1/policyModel/mgmt/{component_type_id}",
        )
        return ComponentType.model_validate(parse_data(response))

    def get_active(self, component_type_id: int) -> ComponentType:
        response = self._client.get(
            f"/console/api/v1/policyModel/mgmt/active/{component_type_id}",
        )
        return ComponentType.model_validate(parse_data(response))

    def create(self, payload: dict[str, object]) -> int:
        response = self._client.post(
            "/console/api/v1/policyModel/mgmt/add",
            json=payload,
        )
        return parse_data(response)

    def modify(self, payload: dict[str, object]) -> int:
        response = self._client.put(
            "/console/api/v1/policyModel/mgmt/modify",
            json=payload,
        )
        return parse_data(response)

    def delete(self, component_type_id: int) -> None:
        response = self._client.delete(
            f"/console/api/v1/policyModel/mgmt/remove/{component_type_id}",
        )
        raise_for_status(response)

    def bulk_delete(self, component_type_ids: list[int]) -> None:
        response = self._client.request(
            "DELETE",
            "/console/api/v1/policyModel/mgmt/bulkDelete",
            json=component_type_ids,
        )
        raise_for_status(response)

    def clone(self, component_type_id: int) -> int:
        response = self._client.post(
            "/console/api/v1/policyModel/mgmt/clone",
            json=component_type_id,
        )
        return parse_data(response)

    def list_extra_subject_attributes(
        self,
        component_type: str,
    ) -> list[AttributeConfig]:
        response = self._client.get(
            f"/console/api/v1/policyModel/mgmt/extraSubjectAttribs/{component_type}",
        )
        raw = parse_data(response)
        return [AttributeConfig.model_validate(entry) for entry in raw]


class AsyncComponentTypeService:

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get(self, component_type_id: int) -> ComponentType:
        resp = await self._client.get(
            f"/console/api/v1/policyModel/mgmt/{component_type_id}",
        )
        return ComponentType.model_validate(parse_data(resp))

    async def get_active(self, component_type_id: int) -> ComponentType:
        resp = await self._client.get(
            f"/console/api/v1/policyModel/mgmt/active/{component_type_id}",
        )
        return ComponentType.model_validate(parse_data(resp))

    async def create(self, payload: dict[str, object]) -> int:
        resp = await self._client.post(
            "/console/api/v1/policyModel/mgmt/add",
            json=payload,
        )
        return parse_data(resp)

    async def modify(self, payload: dict[str, object]) -> int:
        resp = await self._client.put(
            "/console/api/v1/policyModel/mgmt/modify",
            json=payload,
        )
        return parse_data(resp)

    async def delete(self, component_type_id: int) -> None:
        resp = await self._client.delete(
            f"/console/api/v1/policyModel/mgmt/remove/{component_type_id}",
        )
        raise_for_status(resp)

    async def bulk_delete(self, component_type_ids: list[int]) -> None:
        resp = await self._client.request(
            "DELETE",
            "/console/api/v1/policyModel/mgmt/bulkDelete",
            json=component_type_ids,
        )
        raise_for_status(resp)

    async def clone(self, component_type_id: int) -> int:
        resp = await self._client.post(
            "/console/api/v1/policyModel/mgmt/clone",
            json=component_type_id,
        )
        return parse_data(resp)

    async def list_extra_subject_attributes(
        self,
        component_type: str,
    ) -> list[AttributeConfig]:
        resp = await self._client.get(
            f"/console/api/v1/policyModel/mgmt/extraSubjectAttribs/{component_type}",
        )
        raw = parse_data(resp)
        return [AttributeConfig.model_validate(entry) for entry in raw]
