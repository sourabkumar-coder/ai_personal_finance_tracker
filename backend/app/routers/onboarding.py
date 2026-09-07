from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.database import get_db
from app.database.models import Student, Recommendation
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def register_student(student_in: StudentCreate, db: Session = Depends(get_db)):
    """Register a new student profile and initialize welcome guidance."""
    clean_email = student_in.email.strip().lower()

    # Case-insensitive duplicate email check
    existing = db.query(Student).filter(func.lower(Student.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email is already registered.",
        )

    student_data = student_in.model_dump()
    student_data["name"] = student_data["name"].strip()
    student_data["email"] = clean_email
    student_data["currency"] = (student_data.get("currency") or "INR").strip().upper()
    if student_data.get("college_year"):
        student_data["college_year"] = student_data["college_year"].strip()

    student = Student(**student_data)

    try:
        db.add(student)
        db.flush()  # Flush to obtain student.id

        # Generate onboarding welcome recommendation
        welcome_rec = Recommendation(
            student_id=student.id,
            title="Welcome to AI Finance Tracker! 🎯",
            message=(
                f"Welcome aboard, {student.name}! Your monthly allowance is set to "
                f"{student.currency} {student.monthly_allowance:,.2f}. Head to the Budgets section "
                "to set category limits and start tracking your daily expenses."
            ),
            category="Onboarding",
            impact_level="Low",
            is_read=False,
        )
        db.add(welcome_rec)
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register student due to a data conflict.",
        )

    return student


@router.get("/students", response_model=List[StudentResponse])
def list_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db),
):
    """List registered student profiles with pagination."""
    return db.query(Student).order_by(Student.id.asc()).offset(skip).limit(limit).all()


@router.get("/profile/by-email/{email}", response_model=StudentResponse)
def get_student_by_email(email: str, db: Session = Depends(get_db)):
    """Retrieve student profile by email address (case-insensitive)."""
    clean_email = email.strip().lower()
    student = db.query(Student).filter(func.lower(Student.email) == clean_email).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with email '{email}' not found.",
        )
    return student


@router.get("/profile/{student_id}", response_model=StudentResponse)
def get_student_profile(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
):
    """Retrieve student profile by ID."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return student


@router.put("/profile/{student_id}", response_model=StudentResponse)
@router.patch("/profile/{student_id}", response_model=StudentResponse)
def update_student_profile(
    updates: StudentUpdate,
    student_id: int = Path(..., gt=0, description="The ID of the student to update", examples=[1]),
    db: Session = Depends(get_db),
):
    """Update student profile details, email, or monthly allowance (supports PUT and PATCH)."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )

    update_data = updates.model_dump(exclude_unset=True)

    # Validate email uniqueness if email is being updated
    if "email" in update_data and update_data["email"]:
        clean_email = update_data["email"].strip().lower()
        conflict = (
            db.query(Student)
            .filter(func.lower(Student.email) == clean_email, Student.id != student_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email address is already in use by another account.",
            )
        update_data["email"] = clean_email
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "currency" in update_data and update_data["currency"]:
        update_data["currency"] = update_data["currency"].strip().upper()
    if "college_year" in update_data and update_data["college_year"]:
        update_data["college_year"] = update_data["college_year"].strip()

    for key, value in update_data.items():
        setattr(student, key, value)

    try:
        db.commit()
        db.refresh(student)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error while updating profile.",
        )

    return student


@router.delete("/profile/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_profile(
    student_id: int = Path(..., gt=0, description="The ID of the student to delete", examples=[1]),
    db: Session = Depends(get_db),
):
    """Delete a student profile and all associated data (cascaded)."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    db.delete(student)
    db.commit()
    return None
