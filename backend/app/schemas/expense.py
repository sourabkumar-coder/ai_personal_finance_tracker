from datetime import datetime, date as dt_date
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExpenseBase(BaseModel):
    student_id: int
    title: str = Field(..., min_length=1, max_length=200, examples=["Textbook purchase"])
    amount: float = Field(..., gt=0.0, examples=[45.50])
    category: str = Field("Others", examples=["Books"])  # Food, Books, Rent, Entertainment, Travel, Utilities, Others
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

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> dt_date:
        if not v or v == "" or str(v).strip() == "":
            return dt_date.today()
        if isinstance(v, str):
            try:
                return dt_date.fromisoformat(v.strip())
            except ValueError:
                return dt_date.today()
        return v

    @field_validator("title", "category", "payment_method", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip()
        return str(v) if v is not None else ""


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
