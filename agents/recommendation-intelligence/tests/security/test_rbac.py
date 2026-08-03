from gie_security.rbac import PermissionDeniedError
from recommendation_intelligence.domain.rbac import RecommendationPermission, require_recommendation_permission

def test_viewer_cannot_generate():
    try:
        require_recommendation_permission({"viewer"}, RecommendationPermission.REC_GENERATE)
        assert False
    except PermissionDeniedError:
        pass

def test_analyst_can_generate():
    require_recommendation_permission({"analyst"}, RecommendationPermission.REC_GENERATE)

def test_viewer_cannot_approve():
    try:
        require_recommendation_permission({"viewer"}, RecommendationPermission.REC_APPROVE)
        assert False
    except PermissionDeniedError:
        pass

def test_operator_can_approve():
    require_recommendation_permission({"operator"}, RecommendationPermission.REC_APPROVE)
