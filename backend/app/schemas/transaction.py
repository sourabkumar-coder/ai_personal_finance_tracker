from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.expense import ExpenseResponse
from app.schemas.budget import BudgetAlertResponse


class AutoDetectRequest(BaseModel):
    """
    Payload sent from Android Companion App or ingestion endpoint.
    Accepts either pre-extracted fields or raw notification text for backend parsing.
    """
    student_id: int = Field(..., gt=0, examples=[1])
    amount: Optional[float] = Field(None, gt=0.0, examples=[350.0])
    merchant: Optional[str] = Field(None, examples=["Zomato"])
    description: Optional[str] = None
    transaction_type: Optional[str] = Field(None, examples=["EXPENSE"])  # EXPENSE, INCOME
    category: Optional[str] = None
    subcategory: Optional[str] = None
    payment_method: str = Field("UPI", examples=["UPI"])
    source_app: Optional[str] = Field(None, examples=["PhonePe"])
    package_name: Optional[str] = Field(None, examples=["com.phonepe.app"])
    raw_notification: Optional[str] = Field(None, examples=["Payment of ₹350 to Zomato successful"])
    notification_text: Optional[str] = Field(None, examples=["Payment of ₹350 to Zomato successful"])
    notification_title: Optional[str] = None
    reference: Optional[str] = None
    reference_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    status: Optional[str] = Field(None, examples=["SUCCESS"])


class AutoDetectResponse(BaseModel):
    success: bool
    message: str
    is_duplicate: bool = False
    ignored: bool = False
    ignore_reason: Optional[str] = None
    expense: Optional[ExpenseResponse] = None
    parsed_details: Optional[Dict[str, Any]] = None
    budget_alert: Optional[BudgetAlertResponse] = None


class SimulateNotificationRequest(BaseModel):
    """Payload to simulate receiving a notification (for web testing/demo)."""
    student_id: int = Field(..., gt=0, examples=[1])
    notification_text: str = Field(..., min_length=2, examples=["Payment of ₹350 to Zomato successful"])
    notification_title: Optional[str] = Field("Google Pay", examples=["Google Pay"])
    source_app: Optional[str] = Field("PhonePe", examples=["PhonePe"])
    package_name: Optional[str] = Field("com.phonepe.app", examples=["com.phonepe.app"])


class ConfirmCategoryRequest(BaseModel):
    """User confirming or correcting category for a transaction."""
    category: str = Field(..., min_length=1, examples=["Education"])
    subcategory: Optional[str] = None
    save_as_preference: bool = Field(True, description="Learn this preference for future transactions")


class StudentSettingsBase(BaseModel):
    auto_tracking_enabled: bool = True
    auto_categorize_enabled: bool = True
    require_confirmation_low_confidence: bool = True
    device_model: Optional[str] = None


class StudentSettingsUpdate(BaseModel):
    auto_tracking_enabled: Optional[bool] = None
    auto_categorize_enabled: Optional[bool] = None
    require_confirmation_low_confidence: Optional[bool] = None
    device_model: Optional[str] = None


class StudentSettingsResponse(StudentSettingsBase):
    id: int
    student_id: int
    last_device_sync: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TrackingStatusResponse(BaseModel):
    student_id: int
    auto_tracking_enabled: bool
    is_connected: bool
    total_auto_detected: int
    last_detected_at: Optional[datetime] = None
    last_merchant: Optional[str] = None
    last_amount: Optional[float] = None
    supported_apps: List[str]
