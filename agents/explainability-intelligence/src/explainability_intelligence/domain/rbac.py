from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role

class ExplainPermission(StrEnum):
    EXPLAIN_READ = "explainability:read"
    EXPLAIN_GENERATE = "explainability:generate"
    EXPLAIN_ADMIN = "explainability:admin"

ROLE_PERMS = {
    Role.VIEWER: frozenset({ExplainPermission.EXPLAIN_READ}),
    Role.ANALYST: frozenset({ExplainPermission.EXPLAIN_READ, ExplainPermission.EXPLAIN_GENERATE}),
    Role.OPERATOR: frozenset({ExplainPermission.EXPLAIN_READ, ExplainPermission.EXPLAIN_GENERATE}),
    Role.ADMIN: frozenset(set(ExplainPermission)),
}

def require_explain_permission(roles, permission: ExplainPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and ExplainPermission.EXPLAIN_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
