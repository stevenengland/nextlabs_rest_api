from __future__ import annotations

import httpx

from nextlabs_sdk._cloudaz._models import Operator
from nextlabs_sdk._cloudaz._response import parse_data


class OperatorService:

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def list_all(self) -> list[Operator]:
        response = self._client.get("/console/api/v1/config/dataType/list")
        raw = parse_data(response)
        return [Operator.model_validate(entry) for entry in raw]

    def list_by_type(self, data_type: str) -> list[Operator]:
        response = self._client.get(
            f"/console/api/v1/config/dataType/list/{data_type}",
        )
        raw = parse_data(response)
        return [Operator.model_validate(entry) for entry in raw]

    def list_types(self) -> list[str]:
        response = self._client.get("/console/api/v1/config/dataType/types")
        return parse_data(response)
