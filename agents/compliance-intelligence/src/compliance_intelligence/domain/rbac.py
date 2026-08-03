from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role

class CompliancePermission(StrEnum):
    COMPLIANCE_READ = "compliance:read"
    COMPLIANCE_ANALYZE = "compliance:analyze"
    COMPLIANCE_VALIDATE = "compliance:validate"
    COMPLIANCE_ADMIN = "compliance:admin"

ROLE_PERMS = {
    Role.VIEWER: frozenset({CompliancePermission.COMPLIANCE_READ}),
    Role.ANALYST: frozenset({CompliancePermission.COMPLIANCE_READ, CompliancePermission.COMPLIANCE_ANALYZE, CompliancePermission.COMPLIANCE_VALIDATE}),
    Role.OPERATOR: frozenset({CompliancePermission.COMPLIANCE_READ, CompliancePermission.COMPLIANCE_ANALYZE, CompliancePermission.COMPLIANCE_VALIDATE}),
    Role.ADMIN: frozenset(set(CompliancePermission)),
}

def require_compliance_permission(roles, permission: CompliancePermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and CompliancePermission.COMPLIANCE_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
