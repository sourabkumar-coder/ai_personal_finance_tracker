from datetime import date, timedelta
from fastapi.testclient import TestClient


def test_create_and_deposit_goal(client: TestClient):
    # Register student
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "GoalTester", "email": "goaltester@example.com", "monthly_allowance": 5000.0},
    )
    assert reg.status_code == 201
    student_id = reg.json()["id"]

    # Create goal
    deadline_str = (date.today() + timedelta(days=60)).isoformat()
    g_res = client.post(
        "/api/goals/",
        json={
            "student_id": student_id,
            "title": "Emergency Fund",
            "target_amount": 1000.0,
            "current_amount": 200.0,
            "deadline": deadline_str,
        },
    )
    assert g_res.status_code == 201
    goal_data = g_res.json()
    goal_id = goal_data["id"]
    assert goal_data["current_amount"] == 200.0

    # Deposit using POST method (frontend method)
    dep_post = client.post(
        f"/api/goals/{goal_id}/deposit",
        json={"amount": 300.0},
    )
    assert dep_post.status_code == 200
    assert dep_post.json()["current_amount"] == 500.0

    # Deposit using PATCH method
    dep_patch = client.patch(
        f"/api/goals/{goal_id}/deposit",
        json={"amount": 500.0},
    )
    assert dep_patch.status_code == 200
    assert dep_patch.json()["current_amount"] == 1000.0
    assert dep_patch.json()["status"] == "Achieved"
