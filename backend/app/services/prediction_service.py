from datetime import date
import calendar
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.database.models import Student, Expense
from app.utils.helpers import get_current_month_range


class PredictionService:
    @staticmethod
    def forecast_month_end(db: Session, student_id: int) -> Dict[str, Any]:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {}

        today = date.today()
        start_date, end_date = get_current_month_range()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        day_of_month = today.day

        expenses = (
            db.query(Expense)
            .filter(
                Expense.student_id == student_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
            )
            .all()
        )

        total_spent = sum(e.amount for e in expenses)
        allowance = student.monthly_allowance

        # Burn rate per day
        daily_burn_rate = (total_spent / day_of_month) if day_of_month > 0 else 0.0
        projected_total_spent = daily_burn_rate * days_in_month
        projected_end_balance = allowance - projected_total_spent

        will_exceed = projected_total_spent > allowance if allowance > 0 else False
        status = "Critical" if will_exceed else ("Caution" if projected_total_spent > allowance * 0.85 else "Healthy")

        return {
            "student_id": student_id,
            "days_elapsed": day_of_month,
            "days_remaining": days_in_month - day_of_month,
            "current_spent": round(total_spent, 2),
            "daily_burn_rate": round(daily_burn_rate, 2),
            "projected_month_end_spent": round(projected_total_spent, 2),
            "projected_month_end_balance": round(projected_end_balance, 2),
            "will_exceed_allowance": will_exceed,
            "health_status": status,
        }
