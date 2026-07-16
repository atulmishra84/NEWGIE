"""Role-based access control for Context Intelligence API."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    VIEWER = "viewer"
    SCANNER = "scanner"
    ADMIN = "admin"


class Permission(StrEnum):
    SCAN_CREATE = "scan:create"
    SCAN_READ = "scan:read"
    MODEL_READ = "model:read"
    MODEL_DELETE = "model:delete"
    ADMIN_METRICS = "admin:metrics"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.SCAN_READ, Permission.MODEL_READ}),
    Role.SCANNER: frozenset(
        {Permission.SCAN_CREATE, Permission.SCAN_READ, Permission.MODEL_READ}
    ),
    Role.ADMIN: frozenset(Permission),
}


def has_permission(role: Role | str, permission: Permission | str) -> bool:
    try:
        resolved_role = Role(role)
        resolved_perm = Permission(permission)
    except ValueError:
        return False
    return resolved_perm in ROLE_PERMISSIONS.get(resolved_role, frozenset())


def require_permission(role: Role | str, permission: Permission | str) -> None:
    if not has_permission(role, permission):
        raise PermissionError(f"role {role!r} lacks permission {permission!r}")
