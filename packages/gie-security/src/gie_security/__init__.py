"""Authentication and role-based access control for GIE."""

from gie_security.auth import (
    ApiKeyHasher,
    AuthError,
    AuthPrincipal,
    JwtAuthenticator,
    TokenExpiredError,
    TokenInvalidError,
)
from gie_security.rbac import (
    Permission,
    PermissionDeniedError,
    Role,
    ROLE_PERMISSIONS,
    has_permission,
    require_permission,
    require_any_permission,
)

__all__ = [
    "ApiKeyHasher",
    "AuthError",
    "AuthPrincipal",
    "JwtAuthenticator",
    "Permission",
    "PermissionDeniedError",
    "ROLE_PERMISSIONS",
    "Role",
    "TokenExpiredError",
    "TokenInvalidError",
    "has_permission",
    "require_any_permission",
    "require_permission",
]
