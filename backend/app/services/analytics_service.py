from typing import Dict, Any, List
from collections import defaultdict
from sqlalchemy.orm import Session
from app.database.models import Student, Expense
from app.utils.helpers import get_current_month_range, calculate_percentage


class AnalyticsService:
    @staticmethod
    def get_monthly_overview(db: Session, student_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {}

        start_date, end_date = get_current_month_range(year, month)
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
        remaining_balance = max(0.0, allowance - total_spent)
        savings_rate = calculate_percentage(remaining_balance, allowance) if allowance > 0 else 0.0

        return {
            "student_id": student_id,
            "student_name": student.name,
            "currency": student.currency,
            "monthly_allowance": allowance,
            "total_spent": round(total_spent, 2),
            "remaining_balance": round(remaining_balance, 2),
            "savings_rate_pct": savings_rate,
            "expense_count": len(expenses),
            "period": f"{start_date.strftime('%B %Y')}",
        }

    @staticmethod
    def get_category_breakdown(db: Session, student_id: int, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        start_date, end_date = get_current_month_range(year, month)
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
        breakdown = defaultdict(float)
        for e in expenses:
            breakdown[e.category] += e.amount

        results = []
        for cat, amt in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            pct = calculate_percentage(amt, total_spent) if total_spent > 0 else 0.0
            results.append({
                "category": cat,
                "amount": round(amt, 2),
                "percentage": pct,
            })
        return results

    @staticmethod
    def get_spending_trends(db: Session, student_id: int, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        start_date, end_date = get_current_month_range(year, month)
        expenses = (
            db.query(Expense)
            .filter(
                Expense.student_id == student_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
            )
            .order_by(Expense.date.asc())
            .all()
        )

        daily = defaultdict(float)
        for e in expenses:
            daily[e.date.isoformat()] += e.amount

        return [{"date": d, "amount": round(amt, 2)} for d, amt in sorted(daily.items())]
