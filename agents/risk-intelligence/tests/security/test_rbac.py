from gie_security.rbac import PermissionDeniedError
from risk_intelligence.domain.rbac import RiskPermission, require_risk_permission

def test_viewer_cannot_calculate():
    try:
        require_risk_permission({"viewer"}, RiskPermission.RISK_CALCULATE)
        assert False
    except PermissionDeniedError:
        pass

def test_analyst_can_calculate():
    require_risk_permission({"analyst"}, RiskPermission.RISK_CALCULATE)
