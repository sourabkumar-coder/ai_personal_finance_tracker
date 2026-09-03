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


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    amount: Optional[float] = Field(None, gt=0.0)
    category: Optional[str] = None
    date: Optional[dt_date] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ExpenseResponse(ExpenseBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpenseFilter(BaseModel):
    category: Optional[str] = None
    start_date: Optional[dt_date] = None
    end_date: Optional[dt_date] = None
    payment_method: Optional[str] = None
