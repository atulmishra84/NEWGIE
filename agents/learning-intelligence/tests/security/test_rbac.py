from gie_security.rbac import PermissionDeniedError
from learning_intelligence.domain.rbac import (
    LearningPermission,
    require_learning_permission,
)


def test_viewer_cannot_learn():
    try:
        require_learning_permission({"viewer"}, LearningPermission.LEARN_RUN)
        assert False
    except PermissionDeniedError:
        pass


def test_viewer_cannot_approve():
    try:
        require_learning_permission({"viewer"}, LearningPermission.LEARN_APPROVE)
        assert False
    except PermissionDeniedError:
        pass


def test_operator_can_approve():
    require_learning_permission({"operator"}, LearningPermission.LEARN_APPROVE)
