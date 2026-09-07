from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field, ConfigDict, StringConstraints

try:
    import email_validator  # noqa: F401
    from pydantic import EmailStr
except ImportError:
    EmailStr = Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_lower=True,
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        ),
    ]


class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Alex Johnson"])
    email: EmailStr = Field(..., examples=["alex@university.edu"])
    monthly_allowance: float = Field(0.0, ge=0.0, examples=[12000.0])
    currency: str = Field("INR", max_length=10, examples=["INR"])
    college_year: Optional[str] = Field(None, examples=["Sophomore"])


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, examples=["Alex Johnson"])
    email: Optional[EmailStr] = Field(None, examples=["alex_new@university.edu"])
    monthly_allowance: Optional[float] = Field(None, ge=0.0, examples=[15000.0])
    currency: Optional[str] = Field(None, max_length=10, examples=["INR"])
    college_year: Optional[str] = Field(None, examples=["Junior"])


class StudentResponse(StudentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
