from typing import List, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.models import Budget, Expense
from app.utils.helpers import get_current_month_range


class BudgetService:
    @staticmethod
    def get_budget_statuses(db: Session, student_id: int, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        start_date, end_date = get_current_month_range(year, month)
        target_year = start_date.year
        target_month = start_date.month

        budgets = (
            db.query(Budget)
            .filter(
                Budget.student_id == student_id,
                Budget.year == target_year,
                Budget.month == target_month,
            )
            .all()
        )

        statuses = []
        for b in budgets:
            # Query expenses matching category (case-insensitive) in date range
            expenses = (
                db.query(Expense)
                .filter(
                    Expense.student_id == student_id,
                    func.lower(Expense.category) == func.lower(b.category),
                    Expense.date >= start_date,
                    Expense.date <= end_date,
                )
                .all()
            )
            total_spent = sum(e.amount for e in expenses)
            remaining = max(0.0, b.monthly_limit - total_spent)
            percentage = round((total_spent / b.monthly_limit) * 100.0, 2) if b.monthly_limit > 0 else 0.0

            if percentage >= 100:
                status = "Exceeded"
            elif percentage >= 80:
                status = "Warning"
            else:
                status = "Normal"

            statuses.append({
                "budget_id": b.id,
                "category": b.category,
                "monthly_limit": b.monthly_limit,
                "total_spent": round(total_spent, 2),
                "remaining": round(remaining, 2),
                "percentage_used": percentage,
                "status": status,
            })

        return statuses
