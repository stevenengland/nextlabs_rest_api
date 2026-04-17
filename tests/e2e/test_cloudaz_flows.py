"""CloudAz happy-path E2E flows (sync + async)."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from nextlabs_sdk.cloudaz import AsyncCloudAzClient, CloudAzClient, Tag
from tests.e2e._support import StaticBearer

TEST_TOKEN = "e2e-fixture-token"


def test_sync_get_component(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.components.get(component_id=1)
    assert isinstance(result, BaseModel)


def test_sync_get_active_component(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.components.get_active(component_id=1)
    assert isinstance(result, BaseModel)


def test_sync_get_policy(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.policies.get(policy_id=1)
    assert isinstance(result, BaseModel)


def test_sync_get_active_policy(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.policies.get_active(policy_id=1)
    assert isinstance(result, BaseModel)


def test_sync_get_tag(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.tags.get(tag_id=1)
    assert isinstance(result, Tag)


def test_sync_find_policy_dependencies(cloudaz_client: CloudAzClient) -> None:
    result = cloudaz_client.policies.find_dependencies(policy_ids=[1, 2])
    assert isinstance(result, list)


def test_async_get_component(seeded_wiremock: str) -> None:
    async def _run() -> object:
        client = AsyncCloudAzClient(
            base_url=seeded_wiremock,
            auth=StaticBearer(TEST_TOKEN),
        )
        try:
            return await client.components.get(component_id=1)
        finally:
            await client.close()

    assert isinstance(asyncio.run(_run()), BaseModel)


def test_async_get_policy(seeded_wiremock: str) -> None:
    async def _run() -> object:
        client = AsyncCloudAzClient(
            base_url=seeded_wiremock,
            auth=StaticBearer(TEST_TOKEN),
        )
        try:
            return await client.policies.get_active(policy_id=1)
        finally:
            await client.close()

    assert isinstance(asyncio.run(_run()), BaseModel)
