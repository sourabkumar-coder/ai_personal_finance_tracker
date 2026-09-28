from datetime import datetime, date, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    monthly_allowance = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    college_year = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    expenses = relationship("Expense", back_populates="student", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="student", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="student", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="student", cascade="all, delete-orphan")
    category_preferences = relationship("CategoryPreference", back_populates="student", cascade="all, delete-orphan")
    settings = relationship("StudentSettings", back_populates="student", uselist=False, cascade="all, delete-orphan")
    split_groups = relationship("SplitGroup", back_populates="student", cascade="all, delete-orphan")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False)
    payment_method = Column(String(50), default="UPI", nullable=False)
    notes = Column(Text, nullable=True)
    merchant = Column(String(150), nullable=True)
    description = Column(String(255), nullable=True)
    transaction_type = Column(String(20), default="EXPENSE", nullable=False)  # EXPENSE, INCOME
    currency = Column(String(10), default="INR", nullable=False)
    subcategory = Column(String(100), nullable=True)
    source_app = Column(String(100), nullable=True)
    transaction_timestamp = Column(DateTime, nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, PENDING, CANCELLED, UNKNOWN
    confidence = Column(Float, default=1.0, nullable=False)
    is_automatically_detected = Column(Boolean, default=False, nullable=False)
    fingerprint = Column(String(64), unique=True, nullable=True, index=True)
    split_bill_id = Column(Integer, ForeignKey("split_bills.id", ondelete="SET NULL", use_alter=True), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    student = relationship("Student", back_populates="expenses")


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student", back_populates="budgets")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0, nullable=False)
    deadline = Column(Date, nullable=False)
    status = Column(String(50), default="In Progress", nullable=False)  # In Progress, Achieved, Abandoned
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student", back_populates="goals")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    impact_level = Column(String(20), default="Medium")  # Low, Medium, High
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student", back_populates="recommendations")


class SmsAlertLog(Base):
    """
    Dedupe record for outbound budget SMS alerts (TextBee).

    One row per (student, category, month, level) guarantees at most one
    real SMS per category per month per alert level, protecting the
    TextBee daily quota (50 SMS/day on the free tier).
    """

    __tablename__ = "sms_alert_log"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)  # warning | exceeded
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    sent_at = Column(DateTime, default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "student_id", "category", "level", "year", "month",
            name="uq_sms_alert_per_category_month",
        ),
    )


class CategoryPreference(Base):
    """
    Stores user-specific category corrections (e.g. Amazon -> Education)
    so the AI categorizer learns the student's personal preferences.
    """
    __tablename__ = "category_preferences"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    merchant_keyword = Column(String(100), nullable=False, index=True)
    preferred_category = Column(String(100), nullable=False)
    preferred_subcategory = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    student = relationship("Student", back_populates="category_preferences")


class StudentSettings(Base):
    """
    Settings and toggle flags for automatic expense detection and synchronization.
    """
    __tablename__ = "student_settings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False, index=True)
    auto_tracking_enabled = Column(Boolean, default=True, nullable=False)
    auto_categorize_enabled = Column(Boolean, default=True, nullable=False)
    require_confirmation_low_confidence = Column(Boolean, default=True, nullable=False)
    last_device_sync = Column(DateTime, nullable=True)
    device_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    student = relationship("Student", back_populates="settings")


class SplitGroup(Base):
    __tablename__ = "split_groups"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student", back_populates="split_groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    bills = relationship("SplitBill", back_populates="group", cascade="all, delete-orphan")
    settlements = relationship("SplitSettlement", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("split_groups.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=True)
    upi_id = Column(String(100), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    group = relationship("SplitGroup", back_populates="members")
    shares = relationship("SplitBillShare", back_populates="member", cascade="all, delete-orphan")


class SplitBill(Base):
    __tablename__ = "split_bills"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("split_groups.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    total_amount = Column(Float, nullable=False)
    category = Column(String(100), default="Food", nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    payer_name = Column(String(100), default="You", nullable=False)
    payer_member_id = Column(Integer, ForeignKey("group_members.id"), nullable=True)
    split_type = Column(String(20), default="EQUAL", nullable=False)  # EQUAL, EXACT
    notes = Column(Text, nullable=True)
    synced_expense_id = Column(Integer, ForeignKey("expenses.id", ondelete="SET NULL", use_alter=True), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student")
    group = relationship("SplitGroup", back_populates="bills")
    shares = relationship("SplitBillShare", back_populates="bill", cascade="all, delete-orphan")
    synced_expense = relationship("Expense", foreign_keys=[synced_expense_id])


class SplitBillShare(Base):
    __tablename__ = "split_bill_shares"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("split_bills.id"), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("group_members.id"), nullable=True, index=True)
    member_name = Column(String(100), nullable=False)
    share_amount = Column(Float, nullable=False)
    is_settled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    bill = relationship("SplitBill", back_populates="shares")
    member = relationship("GroupMember", back_populates="shares")


class SplitSettlement(Base):
    __tablename__ = "split_settlements"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("split_groups.id"), nullable=True, index=True)
    from_name = Column(String(100), nullable=False)
    to_name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="UPI", nullable=False)
    settlement_date = Column(Date, default=date.today, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    student = relationship("Student")
    group = relationship("SplitGroup", back_populates="settlements")

