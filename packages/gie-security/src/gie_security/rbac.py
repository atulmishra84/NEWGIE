"""Role-based access control for GIE agents."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from gie_security.auth import AuthPrincipal

P = ParamSpec("P")
R = TypeVar("R")


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    OPERATOR = "operator"
    ADMIN = "admin"


class Permission(StrEnum):
    SCAN_READ = "scan:read"
    SCAN_WRITE = "scan:write"
    SCAN_CANCEL = "scan:cancel"
    MODEL_READ = "model:read"
    MODEL_DIFF = "model:diff"
    ADMIN_ALL = "admin:*"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset(
        {
            Permission.SCAN_READ,
            Permission.MODEL_READ,
        }
    ),
    Role.ANALYST: frozenset(
        {
            Permission.SCAN_READ,
            Permission.MODEL_READ,
            Permission.MODEL_DIFF,
        }
    ),
    Role.OPERATOR: frozenset(
        {
            Permission.SCAN_READ,
            Permission.SCAN_WRITE,
            Permission.SCAN_CANCEL,
            Permission.MODEL_READ,
            Permission.MODEL_DIFF,
        }
    ),
    Role.ADMIN: frozenset(set(Permission)),
}


class PermissionDeniedError(Exception):
    """Raised when a principal lacks a required permission."""

    def __init__(
        self, permission: Permission | str, principal: AuthPrincipal | None = None
    ) -> None:
        self.permission = permission
        self.principal = principal
        subject = principal.subject_id if principal else "unknown"
        super().__init__(f"Permission denied: {permission} for subject {subject}")


def _permissions_for_roles(roles: frozenset[str]) -> frozenset[Permission]:
    granted: set[Permission] = set()
    for role_name in roles:
        try:
            role = Role(role_name)
        except ValueError:
            continue
        granted.update(ROLE_PERMISSIONS.get(role, frozenset()))
    return frozenset(granted)


def has_permission(principal: AuthPrincipal, permission: Permission | str) -> bool:
    if Role.ADMIN.value in principal.roles:
        return True
    granted = _permissions_for_roles(principal.roles)
    perm = Permission(permission) if isinstance(permission, str) else permission
    if Permission.ADMIN_ALL in granted:
        return True
    return perm in granted


def require_permission(
    permission: Permission | str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator ensuring the wrapped callable receives an authorized principal."""

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        perm = Permission(permission) if isinstance(permission, str) else permission

        if asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                principal = _extract_principal(args, kwargs)
                if not has_permission(principal, perm):
                    raise PermissionDeniedError(perm, principal)
                return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            principal = _extract_principal(args, kwargs)
            if not has_permission(principal, perm):
                raise PermissionDeniedError(perm, principal)
            return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def require_any_permission(
    *permissions: Permission | str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator requiring at least one of the given permissions."""

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if asyncio.iscoroutinefunction(fn):

            @wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                principal = _extract_principal(args, kwargs)
                if not any(has_permission(principal, perm) for perm in permissions):
                    required = ", ".join(str(p) for p in permissions)
                    raise PermissionDeniedError(required, principal)
                return await fn(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]

        @wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            principal = _extract_principal(args, kwargs)
            if not any(has_permission(principal, perm) for perm in permissions):
                required = ", ".join(str(p) for p in permissions)
                raise PermissionDeniedError(required, principal)
            return fn(*args, **kwargs)

        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _extract_principal(args: tuple[Any, ...], kwargs: dict[str, Any]) -> AuthPrincipal:
    principal = kwargs.get("principal")
    if isinstance(principal, AuthPrincipal):
        return principal
    for value in args:
        if isinstance(value, AuthPrincipal):
            return value
    raise PermissionDeniedError("principal", None)
