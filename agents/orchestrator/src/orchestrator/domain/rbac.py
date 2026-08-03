from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError

class OrchestratorPermission(StrEnum):
    ORCH_READ = "orchestrator:read"
    ORCH_ANALYZE = "orchestrator:analyze"
    ORCH_WORKFLOW = "orchestrator:workflow"
    ORCH_APPROVE = "orchestrator:approve"
    ORCH_ADMIN = "orchestrator:admin"

_ROLE_PERMS: dict[str, set[OrchestratorPermission]] = {
    "viewer": {OrchestratorPermission.ORCH_READ},
    "developer": {
        OrchestratorPermission.ORCH_READ,
        OrchestratorPermission.ORCH_ANALYZE,
        OrchestratorPermission.ORCH_WORKFLOW,
    },
    "operator": {
        OrchestratorPermission.ORCH_READ,
        OrchestratorPermission.ORCH_ANALYZE,
        OrchestratorPermission.ORCH_WORKFLOW,
        OrchestratorPermission.ORCH_APPROVE,
        OrchestratorPermission.ORCH_ADMIN,
    },
    "admin": set(OrchestratorPermission),
}

def require_orch_permission(roles: set[str] | frozenset[str], permission: OrchestratorPermission) -> None:
    allowed: set[OrchestratorPermission] = set()
    for r in roles:
        allowed |= _ROLE_PERMS.get(r, set())
    if permission not in allowed and OrchestratorPermission.ORCH_ADMIN not in allowed:
        raise PermissionDeniedError(f"Missing permission {permission}")
