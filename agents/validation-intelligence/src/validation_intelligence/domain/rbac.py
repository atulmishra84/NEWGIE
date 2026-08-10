from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role


class ValidationPermission(StrEnum):
    VAL_READ = "validation:read"
    VAL_RUN = "validation:run"
    VAL_ADMIN = "validation:admin"


ROLE_PERMS = {
    Role.VIEWER: frozenset({ValidationPermission.VAL_READ}),
    Role.ANALYST: frozenset(
        {ValidationPermission.VAL_READ, ValidationPermission.VAL_RUN}
    ),
    Role.OPERATOR: frozenset(
        {ValidationPermission.VAL_READ, ValidationPermission.VAL_RUN}
    ),
    Role.ADMIN: frozenset(set(ValidationPermission)),
}


def require_validation_permission(roles, permission: ValidationPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and ValidationPermission.VAL_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
