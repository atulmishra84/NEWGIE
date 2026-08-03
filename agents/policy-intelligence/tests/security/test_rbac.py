from gie_security.rbac import PermissionDeniedError

from policy_intelligence.domain.rbac import PolicyPermission, require_policy_permission


def test_viewer_cannot_generate():
    try:
        require_policy_permission({"viewer"}, PolicyPermission.POLICY_GENERATE)
        assert False, "expected deny"
    except PermissionDeniedError:
        pass


def test_analyst_can_generate():
    require_policy_permission({"analyst"}, PolicyPermission.POLICY_GENERATE)
