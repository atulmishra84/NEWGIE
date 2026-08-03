from gie_security.rbac import PermissionDeniedError
from policy_generator.domain.rbac import PolicyGenPermission, require_policygen_permission

def test_viewer_cannot_generate():
    try:
        require_policygen_permission({"viewer"}, PolicyGenPermission.POLICY_GENERATE)
        assert False
    except PermissionDeniedError:
        pass

def test_analyst_can_generate():
    require_policygen_permission({"analyst"}, PolicyGenPermission.POLICY_GENERATE)
