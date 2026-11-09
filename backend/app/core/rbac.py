"""Role based access control for the admin dashboard."""
from typing import Dict, Iterable, Set

from app.models.enums import AdminRole

# Permission keys map 1:1 to dashboard sections and API groups.
PERMISSIONS: Dict[AdminRole, Set[str]] = {
    AdminRole.OWNER: {"*"},
    AdminRole.SUPER_ADMIN: {
        "dashboard.view",
        "analytics.view",
        "products.manage",
        "categories.manage",
        "stock.manage",
        "orders.manage",
        "delivery.manage",
        "payments.view",
        "transactions.view",
        "vouchers.manage",
        "reports.view",
        "customers.manage",
        "tickets.manage",
        "broadcast.manage",
        "settings.manage",
        "logs.view",
    },
    AdminRole.PRODUCT_ADMIN: {
        "dashboard.view",
        "analytics.view",
        "products.manage",
        "categories.manage",
        "stock.manage",
    },
    AdminRole.ORDER_ADMIN: {
        "dashboard.view",
        "orders.manage",
        "delivery.manage",
        "customers.manage",
    },
    AdminRole.FINANCE_ADMIN: {
        "dashboard.view",
        "analytics.view",
        "payments.view",
        "transactions.view",
        "reports.view",
        "vouchers.manage",
    },
    AdminRole.SUPPORT_ADMIN: {
        "dashboard.view",
        "orders.manage",
        "customers.manage",
        "tickets.manage",
    },
}

ALL_PERMISSIONS: Iterable[str] = sorted(
    {perm for perms in PERMISSIONS.values() for perm in perms if perm != "*"}
)


def permissions_for_role(role: AdminRole) -> Set[str]:
    if role is AdminRole.OWNER:
        return set(ALL_PERMISSIONS)
    return set(PERMISSIONS.get(role, set()))


def has_permission(role: AdminRole, permission: str) -> bool:
    """Check a single permission key, honouring the owner wildcard."""
    perms = PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms


def assert_permission(role: AdminRole, permission: str) -> None:
    if not has_permission(role, permission):
        raise PermissionDenied(permission)


class PermissionDenied(Exception):
    """Raised when an admin lacks the required permission."""

    def __init__(self, permission: str) -> None:
        self.permission = permission
        super().__init__(f"Izin ditolak untuk: {permission}")