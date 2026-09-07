from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Student
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _verify_student(student_id: int, db: Session) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return student


@router.get("/{student_id}", response_model=Dict[str, Any])
@router.get("/{student_id}/overview", response_model=Dict[str, Any])
def get_analytics_overview(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month)"),
    db: Session = Depends(get_db),
):
    """Retrieve high-level monthly metrics: total spent, remaining allowance, savings rate."""
    _verify_student(student_id, db)
    return AnalyticsService.get_monthly_overview(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/by-category", response_model=List[Dict[str, Any]])
def get_category_breakdown(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month)"),
    db: Session = Depends(get_db),
):
    """Retrieve categorical distribution of expenditures."""
    _verify_student(student_id, db)
    return AnalyticsService.get_category_breakdown(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/trends", response_model=List[Dict[str, Any]])
def get_spending_trends(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month)"),
    db: Session = Depends(get_db),
):
    """Retrieve daily expenditure trajectory for trend lines."""
    _verify_student(student_id, db)
    return AnalyticsService.get_spending_trends(db, student_id=student_id, year=year, month=month)
