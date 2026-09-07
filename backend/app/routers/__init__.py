"""API Routers package."""
from app.routers.auth import router as auth_router
from app.routers.onboarding import router as onboarding_router
from app.routers.expenses import router as expenses_router
from app.routers.budgets import router as budgets_router
from app.routers.goals import router as goals_router
from app.routers.analytics import router as analytics_router
from app.routers.recommendations import router as recommendations_router
from app.routers.transactions import router as transactions_router

__all__ = [
    "auth_router",
    "onboarding_router",
    "expenses_router",
    "budgets_router",
    "goals_router",
    "analytics_router",
    "recommendations_router",
    "transactions_router",
]
