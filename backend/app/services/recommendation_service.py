from typing import List
from sqlalchemy.orm import Session
from app.database.models import Student, Expense, Budget, Goal, Recommendation
from app.ai.recommendation_engine import RecommendationEngine
from app.utils.helpers import get_current_month_range


class RecommendationService:
    @staticmethod
    def generate_and_save_recommendations(db: Session, student_id: int) -> List[Recommendation]:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return []

        start_date, end_date = get_current_month_range()
        expenses = (
            db.query(Expense)
            .filter(
                Expense.student_id == student_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
            )
            .all()
        )
        budgets = (
            db.query(Budget)
            .filter(
                Budget.student_id == student_id,
                Budget.year == start_date.year,
                Budget.month == start_date.month,
            )
            .all()
        )
        goals = db.query(Goal).filter(Goal.student_id == student_id).all()

        student_dict = {
            "id": student.id,
            "name": student.name,
            "monthly_allowance": student.monthly_allowance,
        }
        expenses_dicts = [
            {"amount": e.amount, "category": e.category, "date": e.date}
            for e in expenses
        ]
        budgets_dicts = [
            {"category": b.category, "monthly_limit": b.monthly_limit}
            for b in budgets
        ]
        goals_dicts = [
            {
                "title": g.title,
                "target_amount": g.target_amount,
                "current_amount": g.current_amount,
                "status": g.status,
            }
            for g in goals
        ]

        # Invoke AI engine
        recs_data = RecommendationEngine.generate_recommendations(
            student_data=student_dict,
            expenses=expenses_dicts,
            budgets=budgets_dicts,
            goals=goals_dicts,
        )

        # Clear older unread AI recommendations (preserve welcome onboarding recommendation)
        db.query(Recommendation).filter(
            Recommendation.student_id == student_id,
            Recommendation.is_read.is_(False),
            Recommendation.category != "Onboarding",
        ).delete(synchronize_session=False)

        created_recs = []
        for r in recs_data:
            rec = Recommendation(
                student_id=student_id,
                title=r["title"],
                message=r["message"],
                category=r["category"],
                impact_level=r["impact_level"],
                is_read=False,
            )
            db.add(rec)
            created_recs.append(rec)

        db.commit()
        for rec in created_recs:
            db.refresh(rec)

        return created_recs
