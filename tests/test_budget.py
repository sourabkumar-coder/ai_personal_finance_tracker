from datetime import date


def test_set_and_get_budget(client):
    today = date.today()
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Charlie", "email": "charlie@school.edu", "monthly_allowance": 700.0},
    )
    student_id = reg.json()["id"]

    # Set budget
    b_res = client.post(
        "/api/budgets/",
        json={
            "student_id": student_id,
            "category": "Food",
            "monthly_limit": 250.0,
            "month": today.month,
            "year": today.year,
        },
    )
    assert b_res.status_code == 201
    assert b_res.json()["monthly_limit"] == 250.0
    budget_id = b_res.json()["id"]

    # Add an expense in food (lowercase to test case-insensitivity)
    client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Grocery store",
            "amount": 100.0,
            "category": "food",
        },
    )

    # Check budget status
    status_res = client.get(f"/api/budgets/{student_id}/status?year={today.year}&month={today.month}")
    assert status_res.status_code == 200
    statuses = status_res.json()
    assert len(statuses) == 1
    assert statuses[0]["total_spent"] == 100.0
    assert statuses[0]["remaining"] == 150.0
    assert statuses[0]["percentage_used"] == 40.0
    assert statuses[0]["status"] == "Normal"

    # Delete budget
    del_res = client.delete(f"/api/budgets/{budget_id}")
    assert del_res.status_code == 204

    # Verify deleted
    all_b = client.get(f"/api/budgets/{student_id}")
    assert len(all_b.json()) == 0
