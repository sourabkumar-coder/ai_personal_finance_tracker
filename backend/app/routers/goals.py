from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Goal, Student
from app.schemas.goal import GoalCreate, GoalDeposit, GoalUpdate, GoalResponse
from app.utils.auth import get_current_student

router = APIRouter(prefix="/api/goals", tags=["Goals"])


def _to_goal_response(goal: Goal) -> GoalResponse:
    r = GoalResponse.model_validate(goal)
    r.progress_percentage = (
        round((goal.current_amount / goal.target_amount) * 100, 2)
        if goal.target_amount > 0
        else 0.0
    )
    return r


@router.post("/", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(
    goal_in: GoalCreate,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Create a new savings goal target."""
    if goal_in.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    student = db.query(Student).filter(Student.id == goal_in.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {goal_in.student_id} not found.",
        )

    goal = Goal(
        student_id=goal_in.student_id,
        title=goal_in.title.strip(),
        target_amount=goal_in.target_amount,
        current_amount=goal_in.current_amount or 0.0,
        deadline=goal_in.deadline,
        status="In Progress",
    )
    if goal.current_amount >= goal.target_amount:
        goal.status = "Achieved"

    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _to_goal_response(goal)


@router.get("/{student_id}", response_model=List[GoalResponse])
def get_student_goals(
    student_id: int = Path(..., gt=0, description="The ID of the student", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """List all goals for a student with computed progress percentage."""
    if student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found.",
        )

    goals = db.query(Goal).filter(Goal.student_id == student_id).order_by(Goal.deadline.asc()).all()
    return [_to_goal_response(g) for g in goals]


@router.post("/{goal_id}/deposit", response_model=GoalResponse)
@router.patch("/{goal_id}/deposit", response_model=GoalResponse)
def deposit_to_goal(
    deposit: GoalDeposit,
    goal_id: int = Path(..., gt=0, description="The ID of the goal", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Add saved funds towards a goal."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if goal and goal.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with ID {goal_id} not found.",
        )

    goal.current_amount = round(goal.current_amount + deposit.amount, 2)
    if goal.current_amount >= goal.target_amount:
        goal.status = "Achieved"

    db.commit()
    db.refresh(goal)
    return _to_goal_response(goal)


@router.put("/{goal_id}", response_model=GoalResponse)
@router.patch("/{goal_id}", response_model=GoalResponse)
def update_goal(
    updates: GoalUpdate,
    goal_id: int = Path(..., gt=0, description="The ID of the goal to update", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Update goal title, target, deadline, or status (supports PUT and PATCH)."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if goal and goal.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with ID {goal_id} not found.",
        )

    data = updates.model_dump(exclude_unset=True)
    if "title" in data and data["title"]:
        data["title"] = data["title"].strip()

    for key, val in data.items():
        setattr(goal, key, val)

    if goal.current_amount >= goal.target_amount and goal.status != "Abandoned":
        goal.status = "Achieved"

    db.commit()
    db.refresh(goal)
    return _to_goal_response(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int = Path(..., gt=0, description="The ID of the goal to delete", examples=[1]),
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    """Delete a goal."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if goal and goal.student_id != current_student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this resource")
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with ID {goal_id} not found.",
        )
    db.delete(goal)
    db.commit()
    return None
