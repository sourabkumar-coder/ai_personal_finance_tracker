"""API Routers package."""
from app.routers.onboarding import router as onboarding_router
from app.routers.expenses import router as expenses_router
from app.routers.budgets import router as budgets_router
from app.routers.goals import router as goals_router
from app.routers.analytics import router as analytics_router
from app.routers.recommendations import router as recommendations_router

__all__ = [
    "onboarding_router",
    "expenses_router",
    "budgets_router",
    "goals_router",
    "analytics_router",
    "recommendations_router",
]
