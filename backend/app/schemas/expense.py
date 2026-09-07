from datetime import datetime, date as dt_date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ExpenseBase(BaseModel):
    student_id: int
    title: str = Field(..., min_length=1, max_length=200, examples=["Textbook purchase"])
    amount: float = Field(..., gt=0.0, examples=[45.50])
    category: str = Field(..., examples=["Books"])  # Food, Books, Rent, Entertainment, Travel, Utilities, Others
    date: dt_date = Field(default_factory=dt_date.today)
    payment_method: str = Field("UPI", examples=["UPI"])  # UPI, Card, Cash, Online
    notes: Optional[str] = Field(None, examples=["Calculus textbook second hand"])
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_type: str = Field("EXPENSE", examples=["EXPENSE"])  # EXPENSE, INCOME
    currency: str = Field("INR", examples=["INR"])
    subcategory: Optional[str] = None
    source_app: Optional[str] = None
    transaction_timestamp: Optional[datetime] = None
    status: str = Field("SUCCESS", examples=["SUCCESS"])
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    is_automatically_detected: bool = False
    fingerprint: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, gt=0.0)
    category: Optional[str] = None
    date: Optional[dt_date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_type: Optional[str] = None
    currency: Optional[str] = None
    subcategory: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None
    is_automatically_detected: Optional[bool] = None


from app.schemas.budget import BudgetAlertResponse


class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    budget_alert: Optional[BudgetAlertResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ExpenseFilter(BaseModel):
    category: Optional[str] = None
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    payment_method: Optional[str] = None
