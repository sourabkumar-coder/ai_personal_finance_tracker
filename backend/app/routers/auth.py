from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.database import get_db
from app.database.models import Student, Recommendation
from app.schemas.student import StudentRegister, StudentResponse, TokenResponse, StudentAuthResponse
from app.utils.auth import get_password_hash, verify_password, create_access_token, get_current_student

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", response_model=StudentAuthResponse, status_code=status.HTTP_201_CREATED)
def register(student_in: StudentRegister, db: Session = Depends(get_db)) -> Any:
    """Register a new student profile and return access token."""
    clean_email = student_in.email.strip().lower()

    existing = db.query(Student).filter(func.lower(Student.email) == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email is already registered.",
        )

    student_data = student_in.model_dump(exclude={"password"})
    student_data["name"] = student_data["name"].strip()
    student_data["email"] = clean_email
    student_data["hashed_password"] = get_password_hash(student_in.password)
    student_data["currency"] = (student_data.get("currency") or "INR").strip().upper()
    if student_data.get("college_year"):
        student_data["college_year"] = student_data["college_year"].strip()

    student = Student(**student_data)

    try:
        db.add(student)
        db.flush()

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

    access_token = create_access_token(data={"sub": str(student.id)})
    return {"student": student, "access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """Login and get access token."""
    student = db.query(Student).filter(func.lower(Student.email) == form_data.username.strip().lower()).first()
    if not student or not verify_password(form_data.password, student.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not student.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(data={"sub": str(student.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=StudentResponse)
def get_current_user_info(current_student: Student = Depends(get_current_student)) -> Any:
    """Get current student profile."""
    return current_student
