from gie_security.rbac import PermissionDeniedError
from compliance_intelligence.domain.rbac import CompliancePermission, require_compliance_permission

def test_viewer_cannot_analyze():
    try:
        require_compliance_permission({"viewer"}, CompliancePermission.COMPLIANCE_ANALYZE)
        assert False
    except PermissionDeniedError:
        pass

def test_analyst_can_analyze():
    require_compliance_permission({"analyst"}, CompliancePermission.COMPLIANCE_ANALYZE)

def test_viewer_can_read():
    require_compliance_permission({"viewer"}, CompliancePermission.COMPLIANCE_READ)
