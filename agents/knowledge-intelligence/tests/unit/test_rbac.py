from gie_security.rbac import PermissionDeniedError

from knowledge_intelligence.domain.rbac import (
    KnowledgePermission,
    require_knowledge_permission,
)


def test_viewer_can_query():
    require_knowledge_permission({"viewer"}, KnowledgePermission.KNOWLEDGE_QUERY)


def test_viewer_cannot_write():
    try:
        require_knowledge_permission({"viewer"}, KnowledgePermission.KNOWLEDGE_WRITE)
        assert False, "expected deny"
    except PermissionDeniedError:
        pass
