from .audit import router as audit_router
from .auth import router as auth_router
from .bi import router as bi_router
from .capacity_building import router as capacity_building_router
from .finance import router as finance_router
from .hr import router as hr_router
from .procurement import router as procurement_router
from .sites import router as sites_router
from .users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "sites_router",
    "hr_router",
    "procurement_router",
    "finance_router",
    "bi_router",
    "capacity_building_router",
    "audit_router",
]
