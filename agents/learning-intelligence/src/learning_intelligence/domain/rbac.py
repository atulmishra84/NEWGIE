from __future__ import annotations
from enum import StrEnum
from gie_security.rbac import PermissionDeniedError, Role


class LearningPermission(StrEnum):
    LEARN_READ = "learning:read"
    LEARN_FEEDBACK = "learning:feedback"
    LEARN_RUN = "learning:run"
    LEARN_APPROVE = "learning:approve"
    LEARN_ADMIN = "learning:admin"


ROLE_PERMS = {
    Role.VIEWER: frozenset({LearningPermission.LEARN_READ}),
    Role.ANALYST: frozenset(
        {
            LearningPermission.LEARN_READ,
            LearningPermission.LEARN_FEEDBACK,
            LearningPermission.LEARN_RUN,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            LearningPermission.LEARN_READ,
            LearningPermission.LEARN_FEEDBACK,
            LearningPermission.LEARN_RUN,
            LearningPermission.LEARN_APPROVE,
        }
    ),
    Role.ADMIN: frozenset(set(LearningPermission)),
}


def require_learning_permission(roles, permission: LearningPermission) -> None:
    granted = set()
    for name in roles:
        try:
            granted.update(ROLE_PERMS.get(Role(name), frozenset()))
        except ValueError:
            continue
    if permission not in granted and LearningPermission.LEARN_ADMIN not in granted:
        raise PermissionDeniedError(str(permission))
