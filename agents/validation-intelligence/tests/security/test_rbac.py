from gie_security.rbac import PermissionDeniedError
from validation_intelligence.domain.rbac import (
    ValidationPermission,
    require_validation_permission,
)


def test_viewer_cannot_run():
    try:
        require_validation_permission({"viewer"}, ValidationPermission.VAL_RUN)
        assert False
    except PermissionDeniedError:
        pass


def test_analyst_can_run():
    require_validation_permission({"analyst"}, ValidationPermission.VAL_RUN)
