from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Alex Johnson"])
    email: EmailStr = Field(..., examples=["alex@university.edu"])
    monthly_allowance: float = Field(0.0, ge=0.0, examples=[500.0])
    currency: str = Field("USD", max_length=10, examples=["USD"])
    college_year: Optional[str] = Field(None, examples=["Sophomore"])


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    monthly_allowance: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field(None, max_length=10)
    college_year: Optional[str] = None


class StudentResponse(StudentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
