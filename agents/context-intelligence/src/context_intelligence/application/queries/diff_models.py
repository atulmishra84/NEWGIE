"""Diff two context models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from gie_security.auth import AuthPrincipal
from gie_security.rbac import Permission, PermissionDeniedError, require_permission

from context_intelligence.application.errors import ModelNotFoundError
from context_intelligence.domain.ports import ContextRepository


@dataclass(frozen=True, slots=True)
class DiffModelsQuery:
    tenant_id: str
    principal: AuthPrincipal
    base_model_id: UUID
    compare_model_id: UUID


@dataclass(frozen=True, slots=True)
class SectionDiff:
    section: str
    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ModelDiffResult:
    base_model_id: UUID
    compare_model_id: UUID
    sections: list[SectionDiff]
    summary: dict[str, int]


class DiffModelsHandler:
    _SECTIONS = (
        "identity",
        "ai",
        "interfaces",
        "data",
        "security",
        "deployment",
        "graph",
    )

    def __init__(self, *, repository: ContextRepository) -> None:
        self._repository = repository

    @require_permission(Permission.MODEL_DIFF)
    async def handle(self, query: DiffModelsQuery) -> ModelDiffResult:
        if query.principal.tenant_id != query.tenant_id:
            raise PermissionDeniedError(Permission.MODEL_DIFF, query.principal)

        base = await self._repository.get_model(query.base_model_id, query.tenant_id)
        if base is None:
            raise ModelNotFoundError(query.base_model_id, query.tenant_id)

        compare = await self._repository.get_model(
            query.compare_model_id, query.tenant_id
        )
        if compare is None:
            raise ModelNotFoundError(query.compare_model_id, query.tenant_id)

        sections: list[SectionDiff] = []
        totals = {"added": 0, "removed": 0, "changed": 0}

        for section_name in self._SECTIONS:
            base_section = getattr(base, section_name).model_dump()
            compare_section = getattr(compare, section_name).model_dump()
            section_diff = self._diff_section(
                section_name, base_section, compare_section
            )
            sections.append(section_diff)
            totals["added"] += len(section_diff.added)
            totals["removed"] += len(section_diff.removed)
            totals["changed"] += len(section_diff.changed)

        return ModelDiffResult(
            base_model_id=query.base_model_id,
            compare_model_id=query.compare_model_id,
            sections=sections,
            summary=totals,
        )

    def _diff_section(
        self,
        section_name: str,
        base: dict[str, Any],
        compare: dict[str, Any],
    ) -> SectionDiff:
        added: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        changed: list[dict[str, Any]] = []

        all_keys = set(base.keys()) | set(compare.keys())
        for key in sorted(all_keys):
            base_value = base.get(key)
            compare_value = compare.get(key)

            if isinstance(base_value, list) and isinstance(compare_value, list):
                base_items = {_item_key(item): item for item in base_value}
                compare_items = {_item_key(item): item for item in compare_value}

                for item_key, item in compare_items.items():
                    if item_key not in base_items:
                        added.append({"field": key, "item": item})
                    elif base_items[item_key] != item:
                        changed.append(
                            {
                                "field": key,
                                "before": base_items[item_key],
                                "after": item,
                            }
                        )

                for item_key, item in base_items.items():
                    if item_key not in compare_items:
                        removed.append({"field": key, "item": item})
            elif base_value != compare_value:
                if base_value is None:
                    added.append({"field": key, "value": compare_value})
                elif compare_value is None:
                    removed.append({"field": key, "value": base_value})
                else:
                    changed.append(
                        {"field": key, "before": base_value, "after": compare_value}
                    )

        return SectionDiff(
            section=section_name, added=added, removed=removed, changed=changed
        )


def _item_key(item: Any) -> str:
    if isinstance(item, dict):
        if "id" in item:
            return f"id:{item['id']}"
        if "name" in item:
            version = item.get("version")
            return f"name:{item['name']}:{version}"
        if "kind" in item and "fingerprint" in item:
            return f"secret:{item['kind']}:{item['fingerprint']}"
        if "source" in item and "target" in item:
            return f"edge:{item['source']}:{item['target']}:{item.get('relationship')}"
    return repr(item)
