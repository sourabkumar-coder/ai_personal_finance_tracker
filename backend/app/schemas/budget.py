from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BudgetBase(BaseModel):
    student_id: int
    category: str = Field(..., examples=["Food"])
    monthly_limit: float = Field(..., gt=0.0, examples=[200.0])
    month: int = Field(..., ge=1, le=12, examples=[9])
    year: int = Field(..., ge=2020, le=2100, examples=[2026])


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    monthly_limit: Optional[float] = Field(None, gt=0.0)


class BudgetResponse(BudgetBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetStatusResponse(BaseModel):
    budget_id: int
    category: str
    monthly_limit: float
    total_spent: float
    remaining: float
    percentage_used: float
    status: str  # Normal, Warning, Exceeded


class BudgetAlertResponse(BaseModel):
    is_exceeded: bool
    is_warning: bool
    category: str
    monthly_limit: float
    total_spent: float
    remaining: float
    percentage_used: float
    message: str

