from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role

class RiskPermission(StrEnum):
    RISK_READ = "risk:read"
    RISK_CALCULATE = "risk:calculate"
    RISK_REMEDIATE = "risk:remediate"
    RISK_ADMIN = "risk:admin"

ROLE_PERMS = {
    Role.VIEWER: frozenset({RiskPermission.RISK_READ}),
    Role.ANALYST: frozenset({RiskPermission.RISK_READ, RiskPermission.RISK_CALCULATE, RiskPermission.RISK_REMEDIATE}),
    Role.OPERATOR: frozenset({RiskPermission.RISK_READ, RiskPermission.RISK_CALCULATE, RiskPermission.RISK_REMEDIATE}),
    Role.ADMIN: frozenset(set(RiskPermission)),
}

def require_risk_permission(roles, permission: RiskPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and RiskPermission.RISK_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
