from __future__ import annotations

from enum import StrEnum

from gie_security.rbac import PermissionDeniedError, Role


class PolicyGenPermission(StrEnum):
    POLICY_READ = "policygen:read"
    POLICY_GENERATE = "policygen:generate"
    POLICY_VALIDATE = "policygen:validate"
    POLICY_ADMIN = "policygen:admin"


ROLE_PERMS = {
    Role.VIEWER: frozenset({PolicyGenPermission.POLICY_READ}),
    Role.ANALYST: frozenset(
        {
            PolicyGenPermission.POLICY_READ,
            PolicyGenPermission.POLICY_GENERATE,
            PolicyGenPermission.POLICY_VALIDATE,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            PolicyGenPermission.POLICY_READ,
            PolicyGenPermission.POLICY_GENERATE,
            PolicyGenPermission.POLICY_VALIDATE,
        }
    ),
    Role.ADMIN: frozenset(set(PolicyGenPermission)),
}


def require_policygen_permission(roles, permission: PolicyGenPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and PolicyGenPermission.POLICY_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
