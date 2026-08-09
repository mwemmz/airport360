from .ai import router as ai_router
from .alerts import router as alerts_router
from .audit import router as audit_router
from .auth import router as auth_router
from .baggage import router as baggage_router
from .bi import router as bi_router
from .bookings import router as bookings_router
from .capacity_building import router as capacity_building_router
from .cargo import router as cargo_router
from .complaints import router as complaints_router
from .computer_vision import router as computer_vision_router
from .finance import router as finance_router
from .flights import router as flights_router
from .hr import router as hr_router
from .incidents import router as incidents_router
from .maintenance import router as maintenance_router
from .ops import router as ops_router
from .passenger import router as passenger_router
from .predictions import router as predictions_router
from .procurement import router as procurement_router
from .queues import router as queues_router
from .sites import router as sites_router
from .travel_agencies import router as travel_agencies_router
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
    "ops_router",
    "flights_router",
    "passenger_router",
    "baggage_router",
    "queues_router",
    "predictions_router",
    "incidents_router",
    "maintenance_router",
    "cargo_router",
    "alerts_router",
    "ai_router",
    "computer_vision_router",
    "complaints_router",
    "travel_agencies_router",
    "bookings_router",
]
