from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.database import get_db
from app.database.models import Student, Expense, Budget, Goal, Recommendation
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.utils.auth import get_current_student

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
    if "hashed_password" not in student_data or not student_data["hashed_password"]:
        student_data["hashed_password"] = ""

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
                f"{student.currency} {student.monthly_allowance:,.2f}. 20% ({student.currency} {student.monthly_allowance * 0.20:,.2f}) "
                "has been automatically synced into your Savings Goal!"
            ),
            category="Onboarding",
            impact_level="Low",
            is_read=False,
        )
        db.add(welcome_rec)
        db.commit()
        db.refresh(student)

        # 20% Auto-Savings Sync for Monthly Allowance
        if student.monthly_allowance > 0:
            from app.services.savings_service import SavingsService
            SavingsService.sync_income_savings(
                db, student_id=student.id, income_amount=student.monthly_allowance, source_description="Monthly Allowance Setup"
            )
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


@router.post("/seed-demo", response_model=StudentResponse)
def seed_demo_student(db: Session = Depends(get_db)):
    """Seed or re-seed demo student profile (Alex Rivera) with sample data."""
    demo_email = "alex.rivera@campus.edu"
    existing = db.query(Student).filter(func.lower(Student.email) == demo_email).first()
    if existing:
        db.delete(existing)
        db.commit()

    student = Student(
        name="Alex Rivera",
        email=demo_email,
        monthly_allowance=850.0,
        currency="INR",
        college_year="Sophomore",
        hashed_password="",
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    today = date.today()
    expenses = [
        Expense(student_id=student.id, title="Campus Dining & Groceries", amount=240.0, category="Food", date=today - timedelta(days=2), payment_method="Card"),
        Expense(student_id=student.id, title="Computer Science Textbook", amount=135.0, category="Books", date=today - timedelta(days=5), payment_method="UPI"),
        Expense(student_id=student.id, title="Weekend Cinema & Arcade", amount=85.0, category="Entertainment", date=today - timedelta(days=1), payment_method="Card"),
        Expense(student_id=student.id, title="Coffee & Study Sessions", amount=35.0, category="Food", date=today, payment_method="Cash"),
        Expense(student_id=student.id, title="Stationery & Supplies", amount=25.0, category="Books", date=today - timedelta(days=3), payment_method="UPI"),
    ]
    for e in expenses:
        db.add(e)

    budgets = [
        Budget(student_id=student.id, category="Food", monthly_limit=220.0, month=today.month, year=today.year),
        Budget(student_id=student.id, category="Entertainment", monthly_limit=90.0, month=today.month, year=today.year),
        Budget(student_id=student.id, category="Books", monthly_limit=150.0, month=today.month, year=today.year),
    ]
    for b in budgets:
        db.add(b)

    goals = [
        Goal(student_id=student.id, title="MacBook Upgrade Fund", target_amount=1200.0, current_amount=950.0, deadline=today + timedelta(days=45), status="In Progress"),
        Goal(student_id=student.id, title="Emergency Savings", target_amount=500.0, current_amount=200.0, deadline=today + timedelta(days=90), status="In Progress"),
    ]
    for g in goals:
        db.add(g)

    rec = Recommendation(
        student_id=student.id,
        title="Welcome Alex! 🎯",
        message="Your demo environment is ready with pre-loaded expenses and budgets.",
        category="Onboarding",
        impact_level="Low",
        is_read=False,
    )
    db.add(rec)
    db.commit()
    db.refresh(student)
    return student


@router.get("/profile/{student_id}", response_model=StudentResponse)
def get_student_profile(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Retrieve student profile by ID."""
    if current_student and current_student.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
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
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Update student profile details, email, or monthly allowance (supports PUT and PATCH)."""
    if current_student and current_student.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
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

        # 20% Auto-Savings Sync if monthly_allowance was updated
        if "monthly_allowance" in update_data and student.monthly_allowance > 0:
            from app.services.savings_service import SavingsService
            SavingsService.sync_income_savings(
                db, student_id=student.id, income_amount=student.monthly_allowance, source_description="Monthly Allowance Update"
            )
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
    current_student: Optional[Student] = Depends(get_current_student),
):
    """Delete a student profile and all associated data (cascaded)."""
    if current_student and current_student.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    db.delete(student)
    db.commit()
    return None
