from gie_security.rbac import PermissionDeniedError
from orchestrator.domain.rbac import OrchestratorPermission, require_orch_permission


def test_viewer_cannot_analyze():
    try:
        require_orch_permission({"viewer"}, OrchestratorPermission.ORCH_ANALYZE)
        assert False
    except PermissionDeniedError:
        pass


def test_operator_can_approve():
    require_orch_permission({"operator"}, OrchestratorPermission.ORCH_APPROVE)
