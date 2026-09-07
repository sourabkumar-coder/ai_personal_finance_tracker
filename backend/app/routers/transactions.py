"""
Transactions & Automatic Expense Detection API Router.
Handles ingestion of parsed/raw notifications from the Android Companion App,
automatic AI categorization, deduplication, user feedback preferences, and settings.
"""
from datetime import datetime, date as dt_date, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Student, Expense, CategoryPreference, StudentSettings
from app.schemas.expense import ExpenseResponse
from app.schemas.transaction import (
    AutoDetectRequest,
    AutoDetectResponse,
    SimulateNotificationRequest,
    ConfirmCategoryRequest,
    StudentSettingsResponse,
    StudentSettingsUpdate,
    TrackingStatusResponse,
)
from app.ai.transaction_parser import TransactionParser, SUPPORTED_PACKAGES, SUPPORTED_APP_NAMES
from app.ai.transaction_categorizer import TransactionCategorizer
from app.services.deduplication_service import DeduplicationService
from app.services.budget_service import BudgetService
from app.utils.auth import get_current_student

router = APIRouter(prefix="/api/transactions", tags=["Automatic Transactions"])


def _get_student(student_id: int, db: Session, current_student: Student) -> Student:
    if student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )
    return student


def _get_or_create_settings(student_id: int, db: Session) -> StudentSettings:
    settings = db.query(StudentSettings).filter(StudentSettings.student_id == student_id).first()
    if not settings:
        settings = StudentSettings(
            student_id=student_id,
            auto_tracking_enabled=True,
            auto_categorize_enabled=True,
            require_confirmation_low_confidence=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.post("/auto-detect", response_model=AutoDetectResponse, status_code=status.HTTP_200_OK)
def auto_detect_transaction(
    payload: AutoDetectRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """
    Ingest and process an automatically detected financial transaction from Android Companion
    or raw notification payload. Applies parsing, deduplication, and AI categorization.
    """
    student = _get_student(payload.student_id, db, current_student)
    settings = _get_or_create_settings(student.id, db)

    # Verify if user has enabled auto-tracking
    if not settings.auto_tracking_enabled:
        return AutoDetectResponse(
            success=False,
            ignored=True,
            message="Automatic expense tracking is disabled in user settings.",
            ignore_reason="Feature disabled by user",
        )

    # 1. Parse details if raw notification is provided or fields missing
    if payload.raw_notification or payload.notification_text or not payload.amount or not payload.merchant:
        raw_text = payload.raw_notification or payload.notification_text or f"{payload.description or ''}"
        parse_result = TransactionParser.parse_notification(
            text=raw_text,
            title=payload.notification_title,
            package_name=payload.package_name,
            source_app=payload.source_app,
        )

        if not parse_result["is_valid_transaction"]:
            return AutoDetectResponse(
                success=False,
                ignored=True,
                message=f"Notification ignored: {parse_result['rejection_reason']}",
                ignore_reason=parse_result["rejection_reason"],
                parsed_details=parse_result,
            )

        amount = parse_result["amount"]
        merchant = parse_result["merchant"]
        transaction_type = parse_result["transaction_type"]
        status_val = parse_result["status"]
        source_app = parse_result["source_app"]
        reference = parse_result["reference"] or payload.reference or payload.reference_id
    else:
        # Structured input provided directly by Android
        amount = payload.amount
        merchant = payload.merchant
        transaction_type = payload.transaction_type or "EXPENSE"
        status_val = payload.status or "SUCCESS"
        source_app = payload.source_app or "UPI App"
        reference = payload.reference or payload.reference_id

        # Validate non-failure status
        if status_val in ["FAILED", "CANCELLED"]:
            return AutoDetectResponse(
                success=False,
                ignored=True,
                message=f"Transaction with status '{status_val}' ignored.",
                ignore_reason=f"Transaction status is {status_val}",
            )

    now = payload.timestamp or datetime.now(timezone.utc)
    txn_date = now.date() if isinstance(now, datetime) else dt_date.today()

    # 2. Deduplication check
    fingerprint = DeduplicationService.generate_fingerprint(
        student_id=student.id,
        amount=amount,
        merchant=merchant,
        txn_date=txn_date,
        reference=reference,
    )

    is_dupe, existing_expense = DeduplicationService.is_duplicate(
        db=db,
        student_id=student.id,
        amount=amount,
        merchant=merchant,
        fingerprint=fingerprint,
        txn_timestamp=now,
    )

    if is_dupe and existing_expense:
        return AutoDetectResponse(
            success=True,
            is_duplicate=True,
            message="Duplicate transaction detected. Ignored to prevent double-counting.",
            expense=ExpenseResponse.model_validate(existing_expense),
        )

    # 3. AI Categorization
    if payload.category and payload.category.strip():
        category = payload.category.strip()
        subcategory = payload.subcategory
        confidence = 1.0
    elif settings.auto_categorize_enabled:
        cat_result = TransactionCategorizer.categorize(
            merchant=merchant,
            amount=amount,
            description=payload.description or payload.raw_notification,
            student_id=student.id,
            db=db,
        )
        category = cat_result["category"]
        subcategory = cat_result.get("subcategory")
        confidence = cat_result.get("confidence", 0.90)
    else:
        category = "Other"
        subcategory = None
        confidence = 0.50

    # 4. Save Expense
    title = merchant or "UPI Transaction"
    notes = f"Auto-detected via {source_app}"
    if reference:
        notes += f" (Ref: {reference})"

    expense = Expense(
        student_id=student.id,
        title=title[:200],
        amount=round(amount, 2),
        category=category,
        date=txn_date,
        payment_method="UPI",
        notes=notes,
        merchant=merchant[:150],
        description=payload.description or f"Payment to {merchant}",
        transaction_type=transaction_type,
        currency=student.currency or "INR",
        subcategory=subcategory[:100] if subcategory else None,
        source_app=source_app[:100],
        transaction_timestamp=now,
        status="SUCCESS",
        confidence=confidence,
        is_automatically_detected=True,
        fingerprint=fingerprint,
    )

    db.add(expense)

    # Update device sync time
    settings.last_device_sync = datetime.now(timezone.utc)
    if payload.package_name:
        settings.device_model = payload.package_name

    db.commit()
    db.refresh(expense)

    alert = BudgetService.check_budget_exceeded(
        db, student_id=student.id, category=category, date_val=txn_date
    )
    alert_model = BudgetAlertResponse.model_validate(alert) if alert else None

    return AutoDetectResponse(
        success=True,
        is_duplicate=False,
        message=f"Transaction of {student.currency} {amount:.2f} at {merchant} automatically recorded as {category}.",
        expense=ExpenseResponse.model_validate(expense),
        parsed_details={
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "source_app": source_app,
        },
        budget_alert=alert_model,
    )


@router.post("/simulate-notification", response_model=AutoDetectResponse)
def simulate_notification(
    req: SimulateNotificationRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """
    Convenience demo endpoint to simulate an incoming payment notification string
    (e.g., 'Payment of ₹350 to Zomato successful') and see instant detection.
    """
    if req.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    detect_req = AutoDetectRequest(
        student_id=req.student_id,
        raw_notification=req.notification_text,
        notification_title=req.notification_title or req.source_app,
        source_app=req.source_app,
        package_name=req.package_name,
    )
    return auto_detect_transaction(detect_req, db, current_student)


@router.get("/{student_id}/status", response_model=TrackingStatusResponse)
def get_tracking_status(
    student_id: int = Path(..., gt=0, description="The ID of the student"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Get the current automatic tracking status, recent detections, and supported apps."""
    student = _get_student(student_id, db, current_student)
    settings = _get_or_create_settings(student.id, db)

    auto_expenses = (
        db.query(Expense)
        .filter(
            Expense.student_id == student_id,
            Expense.is_automatically_detected.is_(True),
        )
        .order_by(Expense.created_at.desc())
    )

    total_count = auto_expenses.count()
    last_expense = auto_expenses.first()

    supported_list = ["Google Pay", "PhonePe", "Paytm", "BHIM UPI", "SBI YONO", "HDFC Bank", "ICICI Bank", "Axis Mobile", "Kotak 811", "Amazon Pay"]

    return TrackingStatusResponse(
        student_id=student.id,
        auto_tracking_enabled=settings.auto_tracking_enabled,
        is_connected=settings.auto_tracking_enabled,
        total_auto_detected=total_count,
        last_detected_at=last_expense.created_at if last_expense else None,
        last_merchant=last_expense.merchant or last_expense.title if last_expense else None,
        last_amount=last_expense.amount if last_expense else None,
        supported_apps=supported_list,
    )


@router.patch("/{expense_id}/confirm", response_model=ExpenseResponse)
def confirm_or_correct_category(
    req: ConfirmCategoryRequest,
    expense_id: int = Path(..., gt=0, description="The ID of the expense to confirm"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """
    Confirm or correct an expense's category.
    Optionally stores this correction in CategoryPreference for future personalized learning.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if expense and expense.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {expense_id} not found.",
        )

    clean_category = req.category.strip()
    expense.category = clean_category
    if req.subcategory:
        expense.subcategory = req.subcategory.strip()
    expense.confidence = 1.0

    # Learn user preference
    if req.save_as_preference and expense.merchant:
        merchant_key = expense.merchant.strip().lower()
        existing_pref = (
            db.query(CategoryPreference)
            .filter(
                CategoryPreference.student_id == expense.student_id,
                CategoryPreference.merchant_keyword == merchant_key,
            )
            .first()
        )
        if existing_pref:
            existing_pref.preferred_category = clean_category
            if req.subcategory:
                existing_pref.preferred_subcategory = req.subcategory.strip()
        else:
            new_pref = CategoryPreference(
                student_id=expense.student_id,
                merchant_keyword=merchant_key,
                preferred_category=clean_category,
                preferred_subcategory=req.subcategory.strip() if req.subcategory else None,
            )
            db.add(new_pref)

    db.commit()
    db.refresh(expense)
    return expense


@router.get("/{student_id}/settings", response_model=StudentSettingsResponse)
def get_student_settings(
    student_id: int = Path(..., gt=0, description="The ID of the student"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Retrieve auto-tracking settings for a student."""
    _get_student(student_id, db, current_student)
    return _get_or_create_settings(student_id, db)


@router.put("/{student_id}/settings", response_model=StudentSettingsResponse)
def update_student_settings(
    updates: StudentSettingsUpdate,
    student_id: int = Path(..., gt=0, description="The ID of the student"),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Update auto-tracking settings for a student."""
    _get_student(student_id, db, current_student)
    settings = _get_or_create_settings(student_id, db)

    update_dict = updates.model_dump(exclude_unset=True)
    for key, val in update_dict.items():
        setattr(settings, key, val)

    db.commit()
    db.refresh(settings)
    return settings
