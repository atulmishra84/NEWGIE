from knowledge_intelligence.domain.rbac import (
    KnowledgePermission,
    has_knowledge_permission,
)


def test_admin_has_all():
    assert has_knowledge_permission({"admin"}, KnowledgePermission.KNOWLEDGE_ADMIN)
    assert has_knowledge_permission({"admin"}, KnowledgePermission.KNOWLEDGE_WRITE)


def test_analyst_readonly():
    assert has_knowledge_permission({"analyst"}, KnowledgePermission.KNOWLEDGE_QUERY)
    assert not has_knowledge_permission(
        {"analyst"}, KnowledgePermission.KNOWLEDGE_REINDEX
    )
