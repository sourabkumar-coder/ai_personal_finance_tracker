from datetime import datetime, date as dt_date
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class GroupMemberCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    upi_id: Optional[str] = None
    student_id: Optional[int] = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    name: str
    email: Optional[str] = None
    upi_id: Optional[str] = None
    student_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SplitGroupCreate(BaseModel):
    student_id: int
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    initial_members: Optional[List[GroupMemberCreate]] = []

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class SplitGroupResponse(BaseModel):
    id: int
    student_id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    members: List[GroupMemberResponse] = []
    bills_count: int = 0
    total_spend: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class SplitBillShareInput(BaseModel):
    member_name: str = Field(..., min_length=1)
    member_id: Optional[int] = None
    share_amount: Optional[float] = None

    @field_validator("member_name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class SplitBillShareResponse(BaseModel):
    id: int
    bill_id: int
    member_id: Optional[int] = None
    member_name: str
    share_amount: float
    is_settled: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SplitBillCreate(BaseModel):
    student_id: int
    group_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=200)
    total_amount: float = Field(..., gt=0.0)
    category: str = Field("Food", min_length=1)
    date: dt_date = Field(default_factory=dt_date.today)
    payer_name: str = Field("You", min_length=1)
    payer_member_id: Optional[int] = None
    split_type: str = Field("EQUAL")  # EQUAL, EXACT
    notes: Optional[str] = None
    shares: List[SplitBillShareInput] = []
    sync_to_expenses: bool = True

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

    @field_validator("title", "category", "payer_name", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class SplitBillResponse(BaseModel):
    id: int
    student_id: int
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    title: str
    total_amount: float
    category: str
    date: dt_date
    payer_name: str
    payer_member_id: Optional[int] = None
    split_type: str
    notes: Optional[str] = None
    synced_expense_id: Optional[int] = None
    created_at: Optional[datetime] = None
    shares: List[SplitBillShareResponse] = []
    your_share: float = 0.0
    your_net_impact: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class SplitSettlementCreate(BaseModel):
    student_id: int
    group_id: Optional[int] = None
    from_name: str = Field(..., min_length=1)
    to_name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0.0)
    payment_method: str = Field("UPI")
    settlement_date: dt_date = Field(default_factory=dt_date.today)
    notes: Optional[str] = None

    @field_validator("settlement_date", mode="before")
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

    @field_validator("from_name", "to_name", "payment_method", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Any) -> str:
        return str(v).strip() if v else ""


class SplitSettlementResponse(BaseModel):
    id: int
    student_id: int
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    from_name: str
    to_name: str
    amount: float
    payment_method: str
    settlement_date: dt_date
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FriendBalance(BaseModel):
    name: str
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    upi_id: Optional[str] = None
    amount_owed_to_you: float = 0.0
    amount_you_owe: float = 0.0
    net_balance: float = 0.0
    status: str  # OWED_TO_YOU, YOU_OWE, SETTLED
    upi_link: Optional[str] = None
    whatsapp_message: Optional[str] = None


class SplitBalanceSummary(BaseModel):
    total_owed_to_you: float = 0.0
    total_you_owe: float = 0.0
    net_balance: float = 0.0
    active_splits_count: int = 0
    friends: List[FriendBalance] = []
