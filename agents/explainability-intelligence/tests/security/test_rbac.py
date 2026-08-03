from gie_security.rbac import PermissionDeniedError
from explainability_intelligence.domain.rbac import ExplainPermission, require_explain_permission

def test_viewer_cannot_generate():
    try:
        require_explain_permission({"viewer"}, ExplainPermission.EXPLAIN_GENERATE)
        assert False
    except PermissionDeniedError:
        pass

def test_analyst_can_generate():
    require_explain_permission({"analyst"}, ExplainPermission.EXPLAIN_GENERATE)
