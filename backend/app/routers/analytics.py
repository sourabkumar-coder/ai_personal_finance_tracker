from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/{student_id}/overview", response_model=Dict[str, Any])
def get_analytics_overview(
    student_id: int,
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve high-level monthly metrics: total spent, remaining allowance, savings rate."""
    return AnalyticsService.get_monthly_overview(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/by-category", response_model=List[Dict[str, Any]])
def get_category_breakdown(
    student_id: int,
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve categorical distribution of expenditures."""
    return AnalyticsService.get_category_breakdown(db, student_id=student_id, year=year, month=month)


@router.get("/{student_id}/trends", response_model=List[Dict[str, Any]])
def get_spending_trends(
    student_id: int,
    year: int = Query(None),
    month: int = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve daily expenditure trajectory for trend lines."""
    return AnalyticsService.get_spending_trends(db, student_id=student_id, year=year, month=month)
