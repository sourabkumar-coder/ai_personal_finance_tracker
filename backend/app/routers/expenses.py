from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Expense, Student
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseResponse

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])


@router.post("/", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense_in: ExpenseCreate, db: Session = Depends(get_db)):
    """Log a new expense entry for a student."""
    student = db.query(Student).filter(Student.id == expense_in.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {expense_in.student_id} not found.",
        )

    data = expense_in.model_dump()
    data["title"] = data["title"].strip()
    data["category"] = data["category"].strip()
    expense = Expense(**data)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/item/{expense_id}", response_model=ExpenseResponse)
def get_single_expense(
    expense_id: int = Path(..., gt=0, description="The ID of the expense", examples=[1]),
    db: Session = Depends(get_db),
):
    """Retrieve a single expense record by ID."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found.",
        )
    return expense


@router.get("/{student_id}", response_model=List[ExpenseResponse])
def get_student_expenses(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    category: Optional[str] = Query(None, description="Filter by category"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    payment_method: Optional[str] = Query(None, description="Filter by payment method"),
    db: Session = Depends(get_db),
):
    """List expenses for a student with optional category and date filtering."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be later than end_date.",
        )

    query = db.query(Expense).filter(Expense.student_id == student_id)
    if category:
        query = query.filter(Expense.category.ilike(f"%{category.strip()}%"))
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)
    if payment_method:
        query = query.filter(Expense.payment_method == payment_method.strip())

    return query.order_by(Expense.date.desc()).all()


@router.put("/{expense_id}", response_model=ExpenseResponse)
@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    updates: ExpenseUpdate,
    expense_id: int = Path(..., gt=0, description="The ID of the expense to update", examples=[1]),
    db: Session = Depends(get_db),
):
    """Update an expense record (supports PUT and PATCH)."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found.",
        )

    update_data = updates.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()
    if "category" in update_data and update_data["category"]:
        update_data["category"] = update_data["category"].strip()

    for key, value in update_data.items():
        setattr(expense, key, value)

    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int = Path(..., gt=0, description="The ID of the expense to delete", examples=[1]),
    db: Session = Depends(get_db),
):
    """Delete an expense record."""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found.",
        )
    db.delete(expense)
    db.commit()
    return None
