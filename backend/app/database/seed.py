from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database.database import SessionLocal, engine, Base
from app.database.models import Student, Expense, Budget, Goal, Recommendation
from app.ai.recommendation_engine import RecommendationEngine


def seed_demo_data_if_empty(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        count = db.query(Student).count()
        if count > 0:
            return

        print("Seeding demo student and financial data...")
        today = date.today()

        student = Student(
            name="Alex Rivera",
            email="alex.rivera@university.edu",
            monthly_allowance=650.0,
            currency="USD",
            college_year="Sophomore",
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        # Expenses
        expenses = [
            Expense(
                student_id=student.id,
                title="Campus Dining & Groceries",
                amount=240.0,
                category="Food",
                date=today - timedelta(days=2),
                payment_method="Card",
                notes="Weekly dining and dorm snacks",
            ),
            Expense(
                student_id=student.id,
                title="Computer Science Textbook",
                amount=135.0,
                category="Books",
                date=today - timedelta(days=5),
                payment_method="UPI",
                notes="Algorithms text and lab manual",
            ),
            Expense(
                student_id=student.id,
                title="Weekend Cinema & Arcade",
                amount=85.0,
                category="Entertainment",
                date=today - timedelta(days=1),
                payment_method="Card",
                notes="Movie night with roommates",
            ),
            Expense(
                student_id=student.id,
                title="Coffee & Study Sessions",
                amount=35.0,
                category="Food",
                date=today,
                payment_method="Cash",
                notes="Campus cafe",
            ),
        ]
        for e in expenses:
            db.add(e)

        # Category Budgets
        budgets = [
            Budget(
                student_id=student.id,
                category="Food",
                monthly_limit=220.0,
                month=today.month,
                year=today.year,
            ),
            Budget(
                student_id=student.id,
                category="Entertainment",
                monthly_limit=90.0,
                month=today.month,
                year=today.year,
            ),
            Budget(
                student_id=student.id,
                category="Books",
                monthly_limit=150.0,
                month=today.month,
                year=today.year,
            ),
        ]
        for b in budgets:
            db.add(b)

        # Savings Goal
        goals = [
            Goal(
                student_id=student.id,
                title="MacBook Upgrade Fund",
                target_amount=1200.0,
                current_amount=950.0,
                deadline=today + timedelta(days=45),
                status="In Progress",
            ),
            Goal(
                student_id=student.id,
                title="Emergency Savings",
                target_amount=500.0,
                current_amount=200.0,
                deadline=today + timedelta(days=90),
                status="In Progress",
            ),
        ]
        for g in goals:
            db.add(g)

        db.commit()

        # Generate initial recommendations
        recs = RecommendationEngine.generate_recommendations(
            student_data={"id": student.id, "name": student.name, "monthly_allowance": student.monthly_allowance},
            expenses=[{"amount": e.amount, "category": e.category} for e in expenses],
            budgets=[{"category": b.category, "monthly_limit": b.monthly_limit} for b in budgets],
            goals=[{"title": g.title, "target_amount": g.target_amount, "current_amount": g.current_amount, "status": g.status} for g in goals],
        )
        for r in recs:
            rec = Recommendation(
                student_id=student.id,
                title=str(r.get("title", "Financial Tip"))[:200],
                message=str(r.get("message", "")),
                category=str(r.get("category", "General"))[:100],
                impact_level=str(r.get("impact_level", "Medium"))[:20],
                is_read=False,
            )
            db.add(rec)
        db.commit()
        print("Demo data seeded successfully with student ID:", student.id)
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_demo_data_if_empty()
