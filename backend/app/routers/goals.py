from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Goal, Student
from app.schemas.goal import GoalCreate, GoalDeposit, GoalUpdate, GoalResponse

router = APIRouter(prefix="/api/goals", tags=["Goals"])


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(goal_in: GoalCreate, db: Session = Depends(get_db)):
    """Create a new savings goal target."""
    student = db.query(Student).filter(Student.id == goal_in.student_id).first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    goal = Goal(
        student_id=goal_in.student_id,
        title=goal_in.title,
        target_amount=goal_in.target_amount,
        current_amount=goal_in.current_amount or 0.0,
        deadline=goal_in.deadline,
        status="In Progress",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    resp = GoalResponse.model_validate(goal)
    resp.progress_percentage = round((goal.current_amount / goal.target_amount) * 100, 2) if goal.target_amount > 0 else 0.0
    return resp


@router.get("/{student_id}", response_model=List[GoalResponse])
def get_student_goals(student_id: int, db: Session = Depends(get_db)):
    """List all goals for a student with computed progress percentage."""
    goals = db.query(Goal).filter(Goal.student_id == student_id).all()
    results = []
    for g in goals:
        r = GoalResponse.model_validate(g)
        r.progress_percentage = round((g.current_amount / g.target_amount) * 100, 2) if g.target_amount > 0 else 0.0
        results.append(r)
    return results


@router.patch("/{goal_id}/deposit", response_model=GoalResponse)
def deposit_to_goal(goal_id: int, deposit: GoalDeposit, db: Session = Depends(get_db)):
    """Add saved funds towards a goal."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    goal.current_amount += deposit.amount
    if goal.current_amount >= goal.target_amount:
        goal.status = "Achieved"

    db.commit()
    db.refresh(goal)

    r = GoalResponse.model_validate(goal)
    r.progress_percentage = round((goal.current_amount / goal.target_amount) * 100, 2) if goal.target_amount > 0 else 0.0
    return r
