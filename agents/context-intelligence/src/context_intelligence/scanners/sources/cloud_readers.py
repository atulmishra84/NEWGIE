"""Cloud provider source readers (Azure, AWS, GCP)."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod

from gie_contracts.sources import (
    AwsSource,
    AzureSource,
    GcpSource,
    ScanSource,
    SourceType,
)

from context_intelligence.scanners.registry import DEFAULT_READER_REGISTRY
from context_intelligence.scanners.sources.base import (
    SourceMaterializationError,
    SourceReader,
    write_metadata,
)
from context_intelligence.scanners.workspace import MaterializedWorkspace


def cloud_scanners_enabled() -> bool:
    return os.environ.get("FLAG_ENABLE_CLOUD_SCANNERS", "false").lower() == "true"


class CloudScannerSkipped(SourceMaterializationError):
    """Cloud scanning disabled or prerequisites missing."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CloudReaderBase(SourceReader, ABC):
    @abstractmethod
    async def _list_resources(self, source: ScanSource) -> dict[str, object]:
        raise NotImplementedError

    async def materialize(self, source: ScanSource) -> MaterializedWorkspace:
        if not cloud_scanners_enabled():
            raise CloudScannerSkipped("FLAG_ENABLE_CLOUD_SCANNERS is not true")

        workspace = MaterializedWorkspace.create(prefix=f"gie-{source.type.value}-")
        payload = await self._list_resources(source)
        (workspace.path / "cloud_resources.json").write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
        write_metadata(workspace, source)
        workspace.compute_digest()
        return workspace


@DEFAULT_READER_REGISTRY.register_reader(SourceType.AZURE)
class AzureCloudReader(CloudReaderBase):
    source_types = frozenset({SourceType.AZURE})

    async def _list_resources(self, source: ScanSource) -> dict[str, object]:
        if not isinstance(source, AzureSource):
            raise SourceMaterializationError("Expected AzureSource")
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.resource import ResourceManagementClient
            from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
        except ImportError as exc:
            raise CloudScannerSkipped("azure SDK not installed") from exc

        credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        resources: dict[str, object] = {"subscription_id": source.subscription_id, "ai_resources": []}

        try:
            cog = CognitiveServicesManagementClient(credential, source.subscription_id)
            for account in cog.accounts.list():
                name = getattr(account, "name", None)
                kind = getattr(account, "kind", None)
                if kind and str(kind).lower() in {"openai", "aiservices", "cognitive"}:
                    resources["ai_resources"].append({"name": name, "kind": kind, "id": account.id})
        except Exception as exc:  # noqa: BLE001
            resources["cognitive_error"] = str(exc)

        if source.resource_group:
            rm = ResourceManagementClient(credential, source.subscription_id)
            try:
                for item in rm.resources.list_by_resource_group(source.resource_group):
                    item_type = getattr(item, "type", "") or ""
                    if any(k in item_type.lower() for k in ("machinelearning", "openai", "cognitive")):
                        resources.setdefault("resource_group_hits", []).append(
                            {"name": item.name, "type": item_type, "id": item.id}
                        )
            except Exception as exc:  # noqa: BLE001
                resources["resource_group_error"] = str(exc)

        if source.resource_ids:
            resources["requested_ids"] = source.resource_ids
        return resources


@DEFAULT_READER_REGISTRY.register_reader(SourceType.AWS)
class AwsCloudReader(CloudReaderBase):
    source_types = frozenset({SourceType.AWS})

    async def _list_resources(self, source: ScanSource) -> dict[str, object]:
        if not isinstance(source, AwsSource):
            raise SourceMaterializationError("Expected AwsSource")
        try:
            import boto3
        except ImportError as exc:
            raise CloudScannerSkipped("boto3 not installed") from exc

        session = boto3.Session(region_name=source.region)
        resources: dict[str, object] = {"region": source.region, "ai_resources": []}

        try:
            bedrock = session.client("bedrock")
            models = bedrock.list_foundation_models()
            resources["bedrock_models"] = [
                m.get("modelId") for m in models.get("modelSummaries", [])
            ]
        except Exception as exc:  # noqa: BLE001
            resources["bedrock_error"] = str(exc)

        try:
            sagemaker = session.client("sagemaker")
            endpoints = sagemaker.list_endpoints(MaxResults=50)
            resources["sagemaker_endpoints"] = [
                e.get("EndpointName") for e in endpoints.get("Endpoints", [])
            ]
        except Exception as exc:  # noqa: BLE001
            resources["sagemaker_error"] = str(exc)

        if source.resource_arns:
            resources["requested_arns"] = source.resource_arns
        return resources


@DEFAULT_READER_REGISTRY.register_reader(SourceType.GCP)
class GcpCloudReader(CloudReaderBase):
    source_types = frozenset({SourceType.GCP})

    async def _list_resources(self, source: ScanSource) -> dict[str, object]:
        if not isinstance(source, GcpSource):
            raise SourceMaterializationError("Expected GcpSource")
        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise CloudScannerSkipped("google-cloud-aiplatform not installed") from exc

        resources: dict[str, object] = {
            "project_id": source.project_id,
            "locations": source.locations,
            "ai_resources": [],
        }
        locations = source.locations or ["us-central1"]
        for location in locations:
            try:
                aiplatform.init(project=source.project_id, location=location)
                # Lightweight listing via API client when available
                resources["ai_resources"].append({"location": location, "initialized": True})
            except Exception as exc:  # noqa: BLE001
                resources.setdefault("errors", []).append({location: str(exc)})

        if source.resource_names:
            resources["requested_names"] = source.resource_names
        return resources
