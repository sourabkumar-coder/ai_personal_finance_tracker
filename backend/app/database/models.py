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

