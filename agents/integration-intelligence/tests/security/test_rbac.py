from gie_security.rbac import PermissionDeniedError
from integration_intelligence.domain.rbac import IntegrationPermission, require_integration_permission

def test_viewer_cannot_connect():
    try:
        require_integration_permission({"viewer"}, IntegrationPermission.INTEGRATION_CONNECT)
        assert False
    except PermissionDeniedError:
        pass

def test_operator_can_admin():
    require_integration_permission({"operator"}, IntegrationPermission.INTEGRATION_ADMIN)
