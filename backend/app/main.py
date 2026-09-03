from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import Base, engine
from app.routers import (
    onboarding_router,
    expenses_router,
    budgets_router,
    goals_router,
    analytics_router,
    recommendations_router,
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Personal Finance Tracker API",
    description="Smart Personal Finance & Budget Management API for Students with AI Insights",
    version="1.0.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(onboarding_router)
app.include_router(expenses_router)
app.include_router(budgets_router)
app.include_router(goals_router)
app.include_router(analytics_router)
app.include_router(recommendations_router)


@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "app": "Personal Finance Tracker API",
        "version": "1.0.0",
    }
