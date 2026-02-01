"""
Role-Based Access Control (RBAC)

Implements authorization checks based on user roles and permissions.
"""

import logging
from collections.abc import Callable
from enum import Enum
from typing import Any

from src.exceptions import ConfigurationError


# Get logger for this module
logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles for RBAC."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


# Define permissions for each role
PERMISSIONS: dict[Role, list[str]] = {
    Role.ADMIN: [
        "workflow:start",
        "workflow:approve",
        "workflow:delete",
        "workflow:view",
        "config:edit",
        "user:manage",
    ],
    Role.DEVELOPER: ["workflow:start", "workflow:approve", "workflow:view"],
    Role.VIEWER: ["workflow:view"],
}


def check_permission(user_roles: list[str], required_permission: str) -> bool:
    """
    Check if any user role has the required permission.

    Args:
        user_roles: List of roles assigned to the user
        required_permission: Permission required to perform an action

    Returns:
        True if user has required permission, False otherwise
    """
    logger.debug(
        "Checking permission",
        extra={"user_roles": user_roles, "required_permission": required_permission},
    )

    # Validate roles
    valid_roles = []
    for role_str in user_roles:
        try:
            valid_roles.append(Role(role_str))
        except ValueError:
            logger.warning(f"Invalid role: {role_str}")
            continue

    # Check if any role has the required permission
    for role in valid_roles:
        if required_permission in PERMISSIONS.get(role, []):
            logger.debug(
                "Permission granted",
                extra={"role": role.value, "permission": required_permission},
            )
            return True

    logger.debug(
        "Permission denied",
        extra={"user_roles": user_roles, "required_permission": required_permission},
    )
    return False


def require_permission(required_permission: str) -> Callable[..., Any]:
    """
    Decorator factory for permission checks.

    Args:
        required_permission: Permission required to access the decorated function

    Returns:
        Decorator function that checks permissions
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: object, **kwargs: object) -> object:
            # Extract user from function arguments
            # This assumes the user object is passed as a keyword argument
            user = kwargs.get("user")
            if not user:
                # Try to find user in args (assuming it's the first argument after self)
                if args and len(args) > 1:
                    user = args[1]
                else:
                    logger.error("No user provided for permission check")
                    raise ConfigurationError(
                        "rbac", "No user provided for permission check"
                    )

            user_roles = user.get("roles", [])
            if not check_permission(user_roles, required_permission):
                logger.warning(
                    "Access denied",
                    extra={
                        "user_id": user.get("sub"),
                        "required_permission": required_permission,
                        "user_roles": user_roles,
                    },
                )
                raise PermissionError(f"Missing permission: {required_permission}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_role_permissions(role: Role) -> list[str]:
    """
    Get all permissions for a specific role.

    Args:
        role: Role to get permissions for

    Returns:
        List of permissions for the role
    """
    return PERMISSIONS.get(role, [])


def list_all_permissions() -> dict[Role, list[str]]:
    """
    List all permissions for all roles.

    Returns:
        Dictionary mapping roles to their permissions
    """
    return PERMISSIONS.copy()
