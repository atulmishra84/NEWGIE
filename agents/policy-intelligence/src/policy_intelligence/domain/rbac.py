from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role


class PolicyPermission(StrEnum):
    POLICY_READ = "policy:read"
    POLICY_GENERATE = "policy:generate"
    POLICY_EXPLAIN = "policy:explain"
    POLICY_ADMIN = "policy:admin"


ROLE_PERMS: dict[Role, frozenset[PolicyPermission]] = {
    Role.VIEWER: frozenset(
        {PolicyPermission.POLICY_READ, PolicyPermission.POLICY_EXPLAIN}
    ),
    Role.ANALYST: frozenset(
        {
            PolicyPermission.POLICY_READ,
            PolicyPermission.POLICY_EXPLAIN,
            PolicyPermission.POLICY_GENERATE,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            PolicyPermission.POLICY_READ,
            PolicyPermission.POLICY_EXPLAIN,
            PolicyPermission.POLICY_GENERATE,
        }
    ),
    Role.ADMIN: frozenset(set(PolicyPermission)),
}


def require_policy_permission(roles, permission: PolicyPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and PolicyPermission.POLICY_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
