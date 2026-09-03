from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {budget_in.student_id} not found.",
        )

    clean_category = budget_in.category.strip()

    # Check if budget already exists for this category/month/year (case-insensitive)
    existing = (
        db.query(Budget)
        .filter(
            Budget.student_id == budget_in.student_id,
            func.lower(Budget.category) == clean_category.lower(),
            Budget.month == budget_in.month,
            Budget.year == budget_in.year,
        )
        .first()
    )

    if existing:
        existing.monthly_limit = budget_in.monthly_limit
        existing.category = clean_category
        db.commit()
        db.refresh(existing)
        return existing

    budget_data = budget_in.model_dump()
    budget_data["category"] = clean_category
    budget = Budget(**budget_data)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{student_id}", response_model=List[BudgetResponse])
def get_student_budgets(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
):
    """Retrieve all defined budgets for a student."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return db.query(Budget).filter(Budget.student_id == student_id).all()


@router.get("/{student_id}/status", response_model=List[BudgetStatusResponse])
def get_budget_statuses(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month)"),
    db: Session = Depends(get_db),
):
    """Retrieve spending vs limit status across categories with warning indicators."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return BudgetService.get_budget_statuses(db, student_id=student_id, year=year, month=month)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int = Path(..., gt=0, description="The ID of the budget to delete", examples=[1]),
    db: Session = Depends(get_db),
):
    """Delete a budget limit."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget with ID {budget_id} not found.",
        )
    db.delete(budget)
    db.commit()
    return None
