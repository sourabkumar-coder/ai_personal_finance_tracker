from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Budget, Student
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetStatusResponse
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def set_or_update_budget(budget_in: BudgetCreate, db: Session = Depends(get_db)):
    """Set or update a budget limit for a category."""
    student = db.query(Student).filter(Student.id == budget_in.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    # Check if budget already exists for this category/month/year
    existing = (
        db.query(Budget)
        .filter(
            Budget.student_id == budget_in.student_id,
            Budget.category == budget_in.category,
            Budget.month == budget_in.month,
            Budget.year == budget_in.year,
        )
        .first()
    )

    if existing:
        existing.monthly_limit = budget_in.monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = Budget(**budget_in.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{student_id}", response_model=List[BudgetResponse])
def get_student_budgets(student_id: int, db: Session = Depends(get_db)):
    """Retrieve all defined budgets for a student."""
    return db.query(Budget).filter(Budget.student_id == student_id).all()


@router.get("/{student_id}/status", response_model=List[BudgetStatusResponse])
def get_budget_statuses(
    student_id: int,
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve spending vs limit status across categories with warning indicators."""
    return BudgetService.get_budget_statuses(db, student_id=student_id, year=year, month=month)
