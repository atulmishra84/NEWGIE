from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError


class IntegrationPermission(StrEnum):
    INTEGRATION_READ = "integration:read"
    INTEGRATION_CONNECT = "integration:connect"
    INTEGRATION_SYNC = "integration:sync"
    INTEGRATION_WEBHOOK = "integration:webhook"
    INTEGRATION_AUTH = "integration:auth"
    INTEGRATION_AUDIT = "integration:audit"
    INTEGRATION_ADMIN = "integration:admin"


_ROLE_PERMS: dict[str, set[IntegrationPermission]] = {
    "viewer": {
        IntegrationPermission.INTEGRATION_READ,
        IntegrationPermission.INTEGRATION_AUDIT,
    },
    "developer": {
        IntegrationPermission.INTEGRATION_READ,
        IntegrationPermission.INTEGRATION_CONNECT,
        IntegrationPermission.INTEGRATION_SYNC,
        IntegrationPermission.INTEGRATION_WEBHOOK,
        IntegrationPermission.INTEGRATION_AUTH,
        IntegrationPermission.INTEGRATION_AUDIT,
    },
    "operator": {
        IntegrationPermission.INTEGRATION_READ,
        IntegrationPermission.INTEGRATION_CONNECT,
        IntegrationPermission.INTEGRATION_SYNC,
        IntegrationPermission.INTEGRATION_WEBHOOK,
        IntegrationPermission.INTEGRATION_AUTH,
        IntegrationPermission.INTEGRATION_AUDIT,
        IntegrationPermission.INTEGRATION_ADMIN,
    },
    "admin": set(IntegrationPermission),
}


def require_integration_permission(
    roles: set[str] | frozenset[str], permission: IntegrationPermission
) -> None:
    allowed: set[IntegrationPermission] = set()
    for r in roles:
        allowed |= _ROLE_PERMS.get(r, set())
    if (
        permission not in allowed
        and IntegrationPermission.INTEGRATION_ADMIN not in allowed
    ):
        raise PermissionDeniedError(f"Missing permission {permission}")
