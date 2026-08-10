"""Unit tests for RBAC."""

from __future__ import annotations

import pytest

from context_intelligence.domain.rbac import (
    Permission,
    Role,
    has_permission,
    require_permission,
)


def test_viewer_can_read_not_create():
    assert has_permission(Role.VIEWER, Permission.MODEL_READ)
    assert has_permission(Role.VIEWER, Permission.SCAN_READ)
    assert not has_permission(Role.VIEWER, Permission.SCAN_CREATE)


def test_scanner_can_create():
    assert has_permission(Role.SCANNER, Permission.SCAN_CREATE)
    assert has_permission(Role.SCANNER, Permission.MODEL_READ)


def test_admin_has_all_permissions():
    for perm in Permission:
        assert has_permission(Role.ADMIN, perm)


def test_require_permission_raises():
    with pytest.raises(PermissionError):
        require_permission(Role.VIEWER, Permission.SCAN_CREATE)


def test_invalid_role_returns_false():
    assert not has_permission("unknown", Permission.SCAN_READ)
