from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Recommendation, Student
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations & AI"])


def _verify_student(student_id: int, db: Session) -> Student:
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return student


@router.get("/{student_id}", response_model=List[RecommendationResponse])
def get_recommendations(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
):
    """Retrieve saved recommendations for a student."""
    _verify_student(student_id, db)
    return (
        db.query(Recommendation)
        .filter(Recommendation.student_id == student_id)
        .order_by(Recommendation.created_at.desc())
        .all()
    )


@router.post("/{student_id}/generate", response_model=List[RecommendationResponse])
def generate_recommendations(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
):
    """Run AI recommendation engine analysis on real spending habits."""
    _verify_student(student_id, db)
    return RecommendationService.generate_and_save_recommendations(db, student_id=student_id)


@router.get("/{student_id}/forecast", response_model=Dict[str, Any])
def forecast_month_end(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
):
    """Predict month-end budget burn rate, projected balance, and health status."""
    _verify_student(student_id, db)
    return PredictionService.forecast_month_end(db, student_id=student_id)


@router.patch("/{recommendation_id}/read", response_model=RecommendationResponse)
def mark_as_read(
    recommendation_id: int = Path(..., gt=0, description="The ID of the recommendation", examples=[1]),
    db: Session = Depends(get_db),
):
    """Mark recommendation notification as read."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with ID {recommendation_id} not found.",
        )
    rec.is_read = True
    db.commit()
    db.refresh(rec)
    return rec


@router.delete("/{recommendation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recommendation(
    recommendation_id: int = Path(..., gt=0, description="The ID of the recommendation to dismiss", examples=[1]),
    db: Session = Depends(get_db),
):
    """Dismiss or delete a recommendation notification."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with ID {recommendation_id} not found.",
        )
    db.delete(rec)
    db.commit()
    return None
