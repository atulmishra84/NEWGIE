from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role

class RecommendationPermission(StrEnum):
    REC_READ = "recommendation:read"
    REC_GENERATE = "recommendation:generate"
    REC_APPROVE = "recommendation:approve"
    REC_ADMIN = "recommendation:admin"

ROLE_PERMS = {
    Role.VIEWER: frozenset({RecommendationPermission.REC_READ}),
    Role.ANALYST: frozenset({RecommendationPermission.REC_READ, RecommendationPermission.REC_GENERATE}),
    Role.OPERATOR: frozenset({RecommendationPermission.REC_READ, RecommendationPermission.REC_GENERATE, RecommendationPermission.REC_APPROVE}),
    Role.ADMIN: frozenset(set(RecommendationPermission)),
}

def require_recommendation_permission(roles, permission: RecommendationPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and RecommendationPermission.REC_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
