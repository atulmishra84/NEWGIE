"""Scan source discriminators for Context Intelligence Agent."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    GIT = "git"
    ZIP = "zip"
    FOLDER = "folder"
    CONTAINER = "container"
    PROCESS = "process"
    KUBERNETES = "kubernetes"
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    GITHUB = "github"
    IDE_WORKSPACE = "ide_workspace"
    CURSOR_PROJECT = "cursor_project"
    VSCODE_WORKSPACE = "vscode_workspace"
    LANGGRAPH = "langgraph"
    OPENAI_AGENTS = "openai_agents"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    SEMANTIC_KERNEL = "semantic_kernel"
    AZURE_AI_FOUNDRY = "azure_ai_foundry"


class _BaseSource(BaseModel):
    type: SourceType
    labels: dict[str, str] = Field(default_factory=dict)


class GitSource(_BaseSource):
    type: Literal[SourceType.GIT] = SourceType.GIT
    url: str
    ref: str = "HEAD"
    depth: int = 1
    token_secret_ref: str | None = None


class ZipSource(_BaseSource):
    type: Literal[SourceType.ZIP] = SourceType.ZIP
    path: str | None = None
    object_uri: str | None = None


class FolderSource(_BaseSource):
    type: Literal[SourceType.FOLDER] = SourceType.FOLDER
    path: str


class ContainerSource(_BaseSource):
    type: Literal[SourceType.CONTAINER] = SourceType.CONTAINER
    image: str
    runtime: Literal["docker", "containerd", "podman"] = "docker"


class ProcessSource(_BaseSource):
    type: Literal[SourceType.PROCESS] = SourceType.PROCESS
    pid: int
    host: str = "localhost"


class KubernetesSource(_BaseSource):
    type: Literal[SourceType.KUBERNETES] = SourceType.KUBERNETES
    context: str | None = None
    namespace: str = "default"
    selectors: dict[str, str] = Field(default_factory=dict)


class AzureSource(_BaseSource):
    type: Literal[SourceType.AZURE] = SourceType.AZURE
    subscription_id: str
    resource_group: str | None = None
    resource_ids: list[str] = Field(default_factory=list)


class AwsSource(_BaseSource):
    type: Literal[SourceType.AWS] = SourceType.AWS
    account_id: str | None = None
    region: str
    resource_arns: list[str] = Field(default_factory=list)


class GcpSource(_BaseSource):
    type: Literal[SourceType.GCP] = SourceType.GCP
    project_id: str
    locations: list[str] = Field(default_factory=list)
    resource_names: list[str] = Field(default_factory=list)


class GitHubSource(_BaseSource):
    type: Literal[SourceType.GITHUB] = SourceType.GITHUB
    owner: str
    repo: str
    ref: str = "main"
    token_secret_ref: str | None = None


class IdeWorkspaceSource(_BaseSource):
    type: Literal[SourceType.IDE_WORKSPACE] = SourceType.IDE_WORKSPACE
    path: str
    ide: Literal["generic", "jetbrains", "eclipse"] = "generic"


class CursorProjectSource(_BaseSource):
    type: Literal[SourceType.CURSOR_PROJECT] = SourceType.CURSOR_PROJECT
    path: str


class VsCodeWorkspaceSource(_BaseSource):
    type: Literal[SourceType.VSCODE_WORKSPACE] = SourceType.VSCODE_WORKSPACE
    path: str
    workspace_file: str | None = None


class FrameworkProjectSource(_BaseSource):
    """Local project path with an expected AI framework hint."""

    type: Literal[
        SourceType.LANGGRAPH,
        SourceType.OPENAI_AGENTS,
        SourceType.CREWAI,
        SourceType.AUTOGEN,
        SourceType.SEMANTIC_KERNEL,
        SourceType.AZURE_AI_FOUNDRY,
    ]
    path: str
    extra: dict[str, Any] = Field(default_factory=dict)


ScanSource = Annotated[
    GitSource
    | ZipSource
    | FolderSource
    | ContainerSource
    | ProcessSource
    | KubernetesSource
    | AzureSource
    | AwsSource
    | GcpSource
    | GitHubSource
    | IdeWorkspaceSource
    | CursorProjectSource
    | VsCodeWorkspaceSource
    | FrameworkProjectSource,
    Field(discriminator="type"),
]
