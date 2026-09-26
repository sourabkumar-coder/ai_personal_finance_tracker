from typing import Dict, Any, List
from collections import defaultdict
from datetime import date, timedelta
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
    def get_spending_trends(
        db: Session,
        student_id: int,
        year: int = None,
        month: int = None,
        granularity: str = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve expenditure trajectory bucketed by granularity.

        - granularity="daily": last 30 days (rolling), one bucket per day.
        - granularity="weekly": last 12 weeks (rolling), buckets anchored on Monday.
        - granularity="monthly": last 12 months (rolling), buckets anchored on 1st.
        - granularity=None (legacy): daily buckets for the given/current month only.

        All buckets are zero-filled and sorted ascending. Each item is
        {"date": ISO start-date, "label": human label, "amount": rounded sum}.
        """
        granularity = (granularity or "").strip().lower() or None
        if granularity is not None and granularity not in ("daily", "weekly", "monthly"):
            raise ValueError("granularity must be one of: daily, weekly, monthly.")

        today = date.today()

        if granularity == "daily":
            end_date = today
            start_date = end_date - timedelta(days=29)
            bucket_keys = [(start_date + timedelta(days=i)) for i in range(30)]

            def bucket_of(d: date) -> date:
                return d

            def label_of(d: date) -> str:
                return d.strftime("%b %d")

        elif granularity == "weekly":
            # Anchor on Monday of current week, go back 11 weeks (12 buckets).
            monday = today - timedelta(days=today.weekday())
            bucket_keys = [monday - timedelta(weeks=i) for i in reversed(range(12))]
            end_date = today
            start_date = bucket_keys[0]

            def bucket_of(d: date) -> date:
                return d - timedelta(days=d.weekday())

            def label_of(d: date) -> str:
                return d.strftime("%b %d")

        elif granularity == "monthly":
            bucket_keys = []
            y, m = today.year, today.month
            for _ in range(12):
                bucket_keys.append(date(y, m, 1))
                m -= 1
                if m == 0:
                    m = 12
                    y -= 1
            bucket_keys.reverse()
            start_date = bucket_keys[0]
            end_date = today

            def bucket_of(d: date) -> date:
                return date(d.year, d.month, 1)

            def label_of(d: date) -> str:
                return d.strftime("%b %Y")

        else:
            # Legacy behavior: daily trajectory for a single calendar month.
            start_date, end_date = get_current_month_range(year, month)

            def bucket_of(d: date) -> date:
                return d

            def label_of(d: date) -> str:
                return d.isoformat()

            bucket_keys = None

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

        totals: Dict[date, float] = defaultdict(float)
        for e in expenses:
            if e.date is None:
                continue
            totals[bucket_of(e.date)] += e.amount or 0.0

        if bucket_keys is not None:
            return [
                {
                    "date": b.isoformat(),
                    "label": label_of(b),
                    "amount": round(totals.get(b, 0.0), 2),
                }
                for b in bucket_keys
            ]

        daily = defaultdict(float)
        for e in expenses:
            daily[e.date.isoformat()] += e.amount

        return [{"date": d, "label": d, "amount": round(amt, 2)} for d, amt in sorted(daily.items())]
