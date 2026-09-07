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


def test_budget_exceeded_notification_alert(client):
    today = date.today()
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Diana", "email": "diana@school.edu", "monthly_allowance": 1000.0},
    )
    student_id = reg.json()["id"]

    # Set Food budget limit of 200.0
    client.post(
        "/api/budgets/",
        json={
            "student_id": student_id,
            "category": "Food",
            "monthly_limit": 200.0,
            "month": today.month,
            "year": today.year,
        },
    )

    # Log expense of 150.0 (Normal spending)
    e1 = client.post(
        "/api/expenses/",
        json={"student_id": student_id, "title": "Lunch", "amount": 150.0, "category": "Food"},
    )
    assert e1.status_code == 201
    assert e1.json()["budget_alert"] is None

    # Log expense of 60.0 (Exceeds 200.0 limit: total 210.0)
    e2 = client.post(
        "/api/expenses/",
        json={"student_id": student_id, "title": "Dinner", "amount": 60.0, "category": "Food"},
    )
    assert e2.status_code == 201
    alert = e2.json()["budget_alert"]
    assert alert is not None
    assert alert["is_exceeded"] is True
    assert alert["total_spent"] == 210.0
    assert alert["percentage_used"] == 105.0
    assert "exceeded" in alert["message"].lower()

    # Query GET /api/budgets/{student_id}/alerts
    alerts_res = client.get(f"/api/budgets/{student_id}/alerts")
    assert alerts_res.status_code == 200
    alerts_list = alerts_res.json()
    assert len(alerts_list) == 1
    assert alerts_list[0]["is_exceeded"] is True
    assert alerts_list[0]["category"] == "Food"

    # Query GET /api/recommendations/{student_id} to ensure persistent recommendation was saved
    recs_res = client.get(f"/api/recommendations/{student_id}")
    assert recs_res.status_code == 200
    recs = recs_res.json()
    assert any("Budget Exceeded" in r["title"] for r in recs)

