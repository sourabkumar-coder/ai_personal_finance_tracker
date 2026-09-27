from datetime import date, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import Goal, Student


class SavingsService:
    @staticmethod
    def sync_income_savings(
        db: Session,
        student_id: int,
        income_amount: float,
        source_description: str = "Income Deposit",
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates 20% of an incoming income deposit and automatically syncs it
        to the student's active Savings Goal (or creates a primary Auto-Savings goal if none exists).
        """
        if income_amount <= 0:
            return None

        savings_amount = round(income_amount * 0.20, 2)

        # Find active 'In Progress' Goal for student, or any latest goal
        goal = (
            db.query(Goal)
            .filter(Goal.student_id == student_id, Goal.status == "In Progress")
            .order_by(Goal.deadline.asc())
            .first()
        )

        if not goal:
            goal = (
                db.query(Goal)
                .filter(Goal.student_id == student_id)
                .order_by(Goal.created_at.desc())
                .first()
            )

        if not goal:
            # Create a default 20% Auto-Savings Goal for student
            today = date.today()
            goal = Goal(
                student_id=student_id,
                title="20% Auto-Savings Target 🎯",
                target_amount=10000.0,
                current_amount=0.0,
                deadline=today + timedelta(days=180),
                status="In Progress",
            )
            db.add(goal)
            db.commit()
            db.refresh(goal)

        # Deposit 20% into goal
        goal.current_amount = round(goal.current_amount + savings_amount, 2)
        if goal.current_amount >= goal.target_amount and goal.status != "Abandoned":
            goal.status = "Achieved"

        db.commit()
        db.refresh(goal)

        student = db.query(Student).filter(Student.id == student_id).first()
        currency_str = student.currency if student else "INR"

        return {
            "synced_amount": savings_amount,
            "income_amount": income_amount,
            "goal_id": goal.id,
            "goal_title": goal.title,
            "goal_current_amount": goal.current_amount,
            "goal_target_amount": goal.target_amount,
            "message": f"20% Auto-Savings Synced! {currency_str} {savings_amount:,.2f} (20% of {currency_str} {income_amount:,.2f}) added to '{goal.title}'.",
        }
