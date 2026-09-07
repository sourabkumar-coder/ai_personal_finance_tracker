from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.models import Budget, Expense, Recommendation
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

    @staticmethod
    def check_budget_exceeded(
        db: Session, student_id: int, category: str, date_val: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Check if an expense pushed spending in category over limit or warning, and save a notification recommendation."""
        if not category:
            return None

        clean_cat = category.strip()
        start_date, end_date = get_current_month_range(
            year=date_val.year if date_val else None,
            month=date_val.month if date_val else None,
        )
        target_year = start_date.year
        target_month = start_date.month

        budget = (
            db.query(Budget)
            .filter(
                Budget.student_id == student_id,
                func.lower(Budget.category) == clean_cat.lower(),
                Budget.year == target_year,
                Budget.month == target_month,
            )
            .first()
        )
        if not budget or budget.monthly_limit <= 0:
            return None

        expenses = (
            db.query(Expense)
            .filter(
                Expense.student_id == student_id,
                func.lower(Expense.category) == clean_cat.lower(),
                Expense.date >= start_date,
                Expense.date <= end_date,
            )
            .all()
        )
        total_spent = sum(e.amount for e in expenses)
        remaining = budget.monthly_limit - total_spent
        percentage = round((total_spent / budget.monthly_limit) * 100.0, 2)

        is_exceeded = percentage >= 100.0
        is_warning = 80.0 <= percentage < 100.0

        if not (is_exceeded or is_warning):
            return None

        if is_exceeded:
            title = f"🚨 Budget Exceeded: {budget.category}"
            message = (
                f"You have exceeded your monthly {budget.category} budget limit! "
                f"Limit: ₹{budget.monthly_limit:,.2f}, Total Spent: ₹{total_spent:,.2f} ({percentage}% used)."
            )
            impact = "High"
        else:
            title = f"🔔 Budget Warning: {budget.category}"
            message = (
                f"You are close to your {budget.category} budget limit! "
                f"Limit: ₹{budget.monthly_limit:,.2f}, Total Spent: ₹{total_spent:,.2f} ({percentage}% used). "
                f"Remaining: ₹{max(0.0, remaining):,.2f}."
            )
            impact = "Medium"

        # Avoid duplicate recommendation if one with exact title already created for student
        existing_rec = (
            db.query(Recommendation)
            .filter(
                Recommendation.student_id == student_id,
                Recommendation.category == budget.category,
                Recommendation.title == title,
            )
            .first()
        )
        if not existing_rec:
            new_rec = Recommendation(
                student_id=student_id,
                title=title[:200],
                message=message,
                category=budget.category[:100],
                impact_level=impact,
                is_read=False,
            )
            db.add(new_rec)
            db.commit()

        return {
            "is_exceeded": is_exceeded,
            "is_warning": is_warning,
            "category": budget.category,
            "monthly_limit": budget.monthly_limit,
            "total_spent": round(total_spent, 2),
            "remaining": round(remaining, 2),
            "percentage_used": percentage,
            "message": message,
        }

    @staticmethod
    def get_budget_alerts(db: Session, student_id: int) -> List[Dict[str, Any]]:
        """Return active exceeded or warning budget alerts for student."""
        statuses = BudgetService.get_budget_statuses(db, student_id)
        alerts = []
        for s in statuses:
            if s["status"] in ["Exceeded", "Warning"]:
                is_exceed = s["status"] == "Exceeded"
                cat = s["category"]
                limit = s["monthly_limit"]
                spent = s["total_spent"]
                pct = s["percentage_used"]
                rem = s["remaining"]

                if is_exceed:
                    msg = f"You have exceeded your monthly {cat} budget limit! Limit: ₹{limit:,.2f}, Spent: ₹{spent:,.2f} ({pct}% used)."
                else:
                    msg = f"You are approaching your {cat} budget limit! Limit: ₹{limit:,.2f}, Spent: ₹{spent:,.2f} ({pct}% used)."

                alerts.append({
                    "is_exceeded": is_exceed,
                    "is_warning": not is_exceed,
                    "category": cat,
                    "monthly_limit": limit,
                    "total_spent": spent,
                    "remaining": rem,
                    "percentage_used": pct,
                    "message": msg,
                })
        return alerts

