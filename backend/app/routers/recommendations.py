from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Recommendation, Student
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService
from app.services.prediction_service import PredictionService
from app.utils.auth import get_current_student

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations & AI"])


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


@router.get("/{student_id}", response_model=List[RecommendationResponse])
def get_recommendations(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    unread_only: bool = Query(False, description="Filter to only unread recommendations"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve saved recommendations for a student with optional unread filter."""
    _verify_student(student_id, db, current_student)
    query = db.query(Recommendation).filter(Recommendation.student_id == student_id)
    if unread_only:
        query = query.filter(Recommendation.is_read.is_(False))
    return query.order_by(Recommendation.created_at.desc()).all()


@router.post("/{student_id}/generate", response_model=List[RecommendationResponse])
def generate_recommendations(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Run AI recommendation engine analysis on real spending habits."""
    _verify_student(student_id, db, current_student)
    return RecommendationService.generate_and_save_recommendations(db, student_id=student_id)


@router.get("/{student_id}/forecast", response_model=Dict[str, Any])
def forecast_month_end(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Predict month-end budget burn rate, projected balance, and health status."""
    _verify_student(student_id, db, current_student)
    return PredictionService.forecast_month_end(db, student_id=student_id)


@router.patch("/{student_id}/read-all", response_model=Dict[str, Any])
def mark_all_as_read(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Mark all unread recommendations for a student as read."""
    _verify_student(student_id, db, current_student)
    updated_count = (
        db.query(Recommendation)
        .filter(
            Recommendation.student_id == student_id,
            Recommendation.is_read.is_(False),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"status": "success", "marked_read_count": updated_count}


@router.patch("/{recommendation_id}/read", response_model=RecommendationResponse)
def mark_as_read(
    recommendation_id: int = Path(..., gt=0, description="The ID of the recommendation", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Mark a single recommendation notification as read."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if rec and rec.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
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
    current_student: Student = Depends(get_current_student),
):
    """Dismiss or delete a recommendation notification."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if rec and rec.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with ID {recommendation_id} not found.",
        )
    db.delete(rec)
    db.commit()
    return None
