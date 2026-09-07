import pytest
from app.ai.recommendation_engine import RecommendationEngine
from app.config import settings


def test_recommendation_and_forecast_flow(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # Register student
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Bruce Banner",
            "email": "bruce@lab.edu",
            "monthly_allowance": 1000.0,
        },
    )
    student_id = reg.json()["id"]

    # Initial welcome recommendation should exist
    recs_res = client.get(f"/api/recommendations/{student_id}")
    assert recs_res.status_code == 200
    initial_recs = recs_res.json()
    assert len(initial_recs) >= 1

    # Log expense
    client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Lab equipment",
            "amount": 800.0,
            "category": "Education",
        },
    )

    # Generate recommendations
    gen_res = client.post(f"/api/recommendations/{student_id}/generate")
    assert gen_res.status_code == 200
    recs = gen_res.json()
    assert len(recs) >= 1
    # 800 out of 1000 is 80% (>75%), so High Burn Rate alert should trigger
    assert any("Burn Rate" in r["title"] for r in recs)

    # Test marking recommendation as read
    rec_id = recs[0]["id"]
    read_res = client.patch(f"/api/recommendations/{rec_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Test unread_only filter
    unread_res = client.get(f"/api/recommendations/{student_id}?unread_only=true")
    assert unread_res.status_code == 200
    assert all(r["is_read"] is False for r in unread_res.json())

    # Test mark-all-as-read
    read_all_res = client.patch(f"/api/recommendations/{student_id}/read-all")
    assert read_all_res.status_code == 200
    assert read_all_res.json()["status"] == "success"

    # Test deleting a recommendation
    del_res = client.delete(f"/api/recommendations/{rec_id}")
    assert del_res.status_code == 204

    # Test forecast endpoint
    forecast_res = client.get(f"/api/recommendations/{student_id}/forecast")
    assert forecast_res.status_code == 200
    forecast = forecast_res.json()
    assert "daily_burn_rate" in forecast
    assert "projected_month_end_spent" in forecast
    assert forecast["current_spent"] == 800.0


def test_rule_based_recommendations_fallback():
    student_data = {"name": "Test Student", "monthly_allowance": 500.0, "currency": "INR"}
    expenses = [{"amount": 400.0, "category": "Food"}]
    budgets = [{"category": "Food", "monthly_limit": 300.0}]
    goals = [{"title": "Trip", "target_amount": 1000.0, "current_amount": 850.0, "status": "In Progress"}]

    recs = RecommendationEngine._generate_rule_based_recommendations(
        student_data=student_data,
        expenses=expenses,
        budgets=budgets,
        goals=goals,
    )
    assert len(recs) >= 1
    titles = [r["title"] for r in recs]
    assert any("Burn Rate" in t for t in titles)
    assert any("Budget Exceeded" in t for t in titles)
    assert any("Goal Almost Complete" in t for t in titles)


def test_recommendation_student_not_found(client):
    res = client.get("/api/recommendations/9999")
    assert res.status_code == 404


def test_rule_based_recommendations_burn_rate():
    student = {"id": 1, "name": "Student", "monthly_allowance": 400.0}
    expenses = [{"amount": 350.0, "category": "Food"}]
    budgets = []
    goals = []

    recs = RecommendationEngine.generate_rule_based_recommendations(
        student, expenses, budgets, goals
    )
    assert len(recs) >= 1
    titles = [r["title"] for r in recs]
    assert any("High Monthly Burn Rate" in t for t in titles)


def test_rule_based_recommendations_budget_exceeded():
    student = {"id": 1, "name": "Student", "monthly_allowance": 500.0}
    expenses = [{"amount": 250.0, "category": "Food"}]
    budgets = [{"category": "Food", "monthly_limit": 200.0}]
    goals = []

    recs = RecommendationEngine.generate_rule_based_recommendations(
        student, expenses, budgets, goals
    )
    assert any("Budget Exceeded in Food" in r["title"] for r in recs)


def test_gemini_fallback_when_api_key_empty(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    student = {"id": 1, "name": "Student", "monthly_allowance": 500.0}
    expenses = [{"amount": 100.0, "category": "General"}]
    budgets = []
    goals = []

    recs = RecommendationEngine.generate_recommendations(student, expenses, budgets, goals)
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert "title" in recs[0]
    assert "message" in recs[0]


def test_gemini_fallback_on_network_error(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "invalid_test_key")
    monkeypatch.setenv("GEMINI_API_KEY", "invalid_test_key")
    student = {"id": 1, "name": "Student", "monthly_allowance": 500.0}
    expenses = [{"amount": 450.0, "category": "Food"}]
    budgets = [{"category": "Food", "monthly_limit": 200.0}]
    goals = []

    # Should not raise exception, but gracefully fall back to heuristics
    recs = RecommendationEngine.generate_recommendations(student, expenses, budgets, goals)
    assert isinstance(recs, list)
    assert len(recs) >= 1
    assert any("Budget Exceeded in Food" in r["title"] for r in recs)


def test_recommendations_api_flow(client, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    # 1. Register student
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "David Miller",
            "email": "david@university.edu",
            "monthly_allowance": 500.0,
            "currency": "INR",
        },
    )
    assert reg.status_code == 201
    student_id = reg.json()["id"]

    # 2. Add an expense
    exp = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Grocery Run",
            "amount": 220.0,
            "category": "Food",
            "date": "2026-09-03",
            "payment_method": "Card",
        },
    )
    assert exp.status_code == 201

    # 3. Add a category budget
    bgt = client.post(
        "/api/budgets/",
        json={
            "student_id": student_id,
            "category": "Food",
            "monthly_limit": 200.0,
            "month": 9,
            "year": 2026,
        },
    )
    assert bgt.status_code == 201

    # 4. Add a savings goal
    gl = client.post(
        "/api/goals/",
        json={
            "student_id": student_id,
            "title": "Textbooks",
            "target_amount": 300.0,
            "current_amount": 250.0,
            "deadline": "2026-10-01",
        },
    )
    assert gl.status_code == 201

    # 5. Generate recommendations via API
    gen_resp = client.post(f"/api/recommendations/{student_id}/generate")
    assert gen_resp.status_code == 200
    recs = gen_resp.json()
    assert isinstance(recs, list)
    assert len(recs) >= 1
    rec_id = recs[0]["id"]
    assert recs[0]["student_id"] == student_id
    assert recs[0]["is_read"] is False

    # 6. Retrieve recommendations
    get_resp = client.get(f"/api/recommendations/{student_id}")
    assert get_resp.status_code == 200
    assert len(get_resp.json()) >= 1

    # 7. Mark recommendation as read
    read_resp = client.patch(f"/api/recommendations/{rec_id}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # 8. Forecast endpoint
    fc_resp = client.get(f"/api/recommendations/{student_id}/forecast")
    assert fc_resp.status_code == 200
    fc = fc_resp.json()
    assert "projected_month_end_spent" in fc
    assert "health_status" in fc
