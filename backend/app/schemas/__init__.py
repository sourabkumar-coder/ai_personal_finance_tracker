"""Pydantic schemas package."""
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse, ExpenseFilter
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetStatusResponse
from app.schemas.goal import GoalCreate, GoalUpdate, GoalDeposit, GoalResponse
from app.schemas.recommendation import RecommendationCreate, RecommendationResponse

__all__ = [
    "StudentCreate",
    "StudentUpdate",
    "StudentResponse",
    "ExpenseCreate",
    "ExpenseUpdate",
    "ExpenseResponse",
    "ExpenseFilter",
    "BudgetCreate",
    "BudgetUpdate",
    "BudgetResponse",
    "BudgetStatusResponse",
    "GoalCreate",
    "GoalUpdate",
    "GoalDeposit",
    "GoalResponse",
    "RecommendationCreate",
    "RecommendationResponse",
]
