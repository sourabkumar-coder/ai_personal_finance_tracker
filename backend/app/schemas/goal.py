from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class GoalBase(BaseModel):
    student_id: int
    title: str = Field(..., min_length=1, max_length=200, examples=["Emergency Fund"])
    target_amount: float = Field(..., gt=0.0, examples=[1000.0])
    current_amount: float = Field(0.0, ge=0.0, examples=[250.0])
    deadline: date = Field(..., examples=["2026-12-31"])
    status: str = Field("In Progress", examples=["In Progress"])


class GoalCreate(BaseModel):
    student_id: int
    title: str = Field(..., min_length=1, max_length=200, examples=["New Laptop"])
    target_amount: float = Field(..., gt=0.0, examples=[800.0])
    current_amount: Optional[float] = Field(0.0, ge=0.0)
    deadline: date


class GoalDeposit(BaseModel):
    amount: float = Field(..., gt=0.0, examples=[50.0])


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    target_amount: Optional[float] = Field(None, gt=0.0)
    deadline: Optional[date] = None
    status: Optional[str] = None


class GoalResponse(GoalBase):
    id: int
    progress_percentage: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
