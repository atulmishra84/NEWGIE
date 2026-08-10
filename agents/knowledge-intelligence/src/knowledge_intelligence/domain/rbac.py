"""Knowledge-specific RBAC permissions (extends gie-security roles)."""

from __future__ import annotations

from enum import StrEnum

from gie_security.rbac import PermissionDeniedError, Role


class KnowledgePermission(StrEnum):
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_QUERY = "knowledge:query"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_VERSION = "knowledge:version"
    KNOWLEDGE_REINDEX = "knowledge:reindex"
    KNOWLEDGE_ADMIN = "knowledge:admin"


ROLE_KNOWLEDGE_PERMISSIONS: dict[Role, frozenset[KnowledgePermission]] = {
    Role.VIEWER: frozenset(
        {KnowledgePermission.KNOWLEDGE_READ, KnowledgePermission.KNOWLEDGE_QUERY}
    ),
    Role.ANALYST: frozenset(
        {
            KnowledgePermission.KNOWLEDGE_READ,
            KnowledgePermission.KNOWLEDGE_QUERY,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            KnowledgePermission.KNOWLEDGE_READ,
            KnowledgePermission.KNOWLEDGE_QUERY,
            KnowledgePermission.KNOWLEDGE_WRITE,
            KnowledgePermission.KNOWLEDGE_VERSION,
            KnowledgePermission.KNOWLEDGE_REINDEX,
        }
    ),
    Role.ADMIN: frozenset(set(KnowledgePermission)),
}


def has_knowledge_permission(
    roles: frozenset[str] | set[str] | list[str], permission: KnowledgePermission
) -> bool:
    granted: set[KnowledgePermission] = set()
    for name in roles:
        try:
            role = Role(name)
        except ValueError:
            continue
        granted.update(ROLE_KNOWLEDGE_PERMISSIONS.get(role, frozenset()))
    return permission in granted or KnowledgePermission.KNOWLEDGE_ADMIN in granted


def require_knowledge_permission(
    roles: frozenset[str] | set[str] | list[str], permission: KnowledgePermission
) -> None:
    if not has_knowledge_permission(roles, permission):
        raise PermissionDeniedError(str(permission))
