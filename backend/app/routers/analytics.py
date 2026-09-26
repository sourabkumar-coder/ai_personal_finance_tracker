from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Student
from app.services.analytics_service import AnalyticsService
from app.utils.auth import get_current_student

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def _verify_student(student_id: int, db: Session, current_student: Student) -> Student:
    if student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
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
    current_student: Student = Depends(get_current_student),
):
    """Retrieve high-level monthly metrics: total spent, remaining allowance, savings rate."""
    _verify_student(student_id, db, current_student)
    return AnalyticsService.get_monthly_overview(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/by-category", response_model=List[Dict[str, Any]])
def get_category_breakdown(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month)"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve categorical distribution of expenditures."""
    _verify_student(student_id, db, current_student)
    return AnalyticsService.get_category_breakdown(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/trends", response_model=List[Dict[str, Any]])
def get_spending_trends(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    year: int = Query(None, description="Filter by year (defaults to current year, legacy mode only)"),
    month: int = Query(None, ge=1, le=12, description="Filter by month (1-12, defaults to current month, legacy mode only)"),
    granularity: str = Query(
        None,
        description="Bucket size: daily (last 30d), weekly (last 12w), monthly (last 12m). Omit for legacy current-month daily.",
        examples=["daily"],
    ),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve expenditure trajectory for trend lines (x=time vs y=spent)."""
    _verify_student(student_id, db, current_student)
    normalized = (granularity or "").strip().lower() or None
    if normalized not in (None, "daily", "weekly", "monthly"):
        raise HTTPException(
            status_code=422,
            detail="granularity must be one of: daily, weekly, monthly.",
        )
    try:
        return AnalyticsService.get_spending_trends(
            db, student_id=student_id, year=year, month=month, granularity=normalized
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
