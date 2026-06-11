"""CloudAz happy-path E2E flows (sync + async)."""

from __future__ import annotations

import asyncio

import httpx
from pydantic import BaseModel

from nextlabs_sdk.cloudaz import (
    AsyncCloudAzClient,
    CloudAzClient,
    Component,
    ComponentHistoryEntry,
    ComponentRevision,
    Tag,
)
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


def test_sync_component_history_then_revision(
    cloudaz_client: CloudAzClient, seeded_wiremock: str
) -> None:
    component_detail = {
        "id": 101,
        "name": "Security Vulnerabilities",
        "type": "RESOURCE",
        "status": "DRAFT",
        "tags": [],
        "conditions": [],
        "memberConditions": [],
        "subComponents": [],
        "actions": [],
        "deployed": False,
        "deploymentTime": 0,
        "revisionCount": 1,
        "ownerId": 0,
        "ownerDisplayName": "Administrator",
        "createdDate": 1713171640267,
        "modifiedById": 0,
        "modifiedBy": "Administrator",
        "lastUpdatedDate": 1713171640252,
    }
    entry = {
        "id": 101,
        "revision": "1",
        "name": "ROOT_101/security",
        "componentDetail": None,
        "createdDate": 1713171640267,
        "createdBy": "Administrator",
        "modifiedBy": "Administrator",
        "lastUpdatedDate": 1713171640252,
        "actionType": "UN",
    }
    history_body = {
        "statusCode": "1003",
        "message": "Data found successfully",
        "data": [entry],
        "pageNo": 1,
        "pageSize": 1,
        "totalPages": 1,
        "totalNoOfRecords": 1,
    }
    revision_body = {
        "statusCode": "1003",
        "message": "Data found successfully",
        "data": {**entry, "componentDetail": component_detail},
    }
    for url_path, body in (
        ("/console/api/v1/component/mgmt/history/101", history_body),
        ("/console/api/v1/component/mgmt/viewRevision/101/1", revision_body),
    ):
        resp = httpx.post(
            f"{seeded_wiremock}/__admin/mappings",
            json={
                "request": {"method": "GET", "urlPath": url_path},
                "response": {
                    "status": 200,
                    "headers": {"Content-Type": "application/json"},
                    "jsonBody": body,
                },
            },
            timeout=5.0,
        )
        resp.raise_for_status()

    history = cloudaz_client.components.list_history(component_id=101)
    assert len(history) == 1
    assert isinstance(history[0], ComponentHistoryEntry)
    assert history[0].revision == 1

    revision = cloudaz_client.components.get_revision(revision_id=101, revision=1)
    assert isinstance(revision, ComponentRevision)
    assert revision.revision == 1
    assert isinstance(revision.component_detail, Component)
    assert revision.component_detail.id == 101


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
