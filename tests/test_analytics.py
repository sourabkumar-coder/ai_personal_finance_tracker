from datetime import date


def test_analytics_overview_and_breakdown(client):
    today = date.today()
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Diana Prince", "email": "diana@school.edu", "monthly_allowance": 1000.0},
    )
    student_id = reg.json()["id"]

    # Log two expenses
    client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Books",
            "amount": 200.0,
            "category": "Education",
        },
    )
    client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Lunch",
            "amount": 50.0,
            "category": "Food",
        },
    )

    # Test monthly overview
    ov_res = client.get(f"/api/analytics/{student_id}/overview?year={today.year}&month={today.month}")
    assert ov_res.status_code == 200
    ov = ov_res.json()
    assert ov["total_spent"] == 250.0
    assert ov["remaining_balance"] == 750.0
    assert ov["savings_rate_pct"] == 75.0

    # Test category breakdown
    cat_res = client.get(f"/api/analytics/{student_id}/by-category?year={today.year}&month={today.month}")
    assert cat_res.status_code == 200
    breakdown = cat_res.json()
    assert len(breakdown) == 2
    # Education should be top since 200 > 50
    assert breakdown[0]["category"] == "Education"
    assert breakdown[0]["amount"] == 200.0


def test_analytics_student_not_found(client):
    res = client.get("/api/analytics/9999/overview")
    assert res.status_code == 404
