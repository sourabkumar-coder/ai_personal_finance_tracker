from datetime import date, timedelta


def _register_student(client, name="Trend User", email="trend@school.edu"):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": name, "email": email, "monthly_allowance": 5000.0},
    )
    assert reg.status_code in (200, 201), reg.text
    return reg.json()["id"]


def _log_expense(client, student_id, amount, day, category="Food", title="Test"):
    res = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": title,
            "amount": amount,
            "category": category,
            "date": day.isoformat(),
        },
    )
    assert res.status_code == 201, res.text


def test_trends_daily_weekly_monthly(client):
    student_id = _register_student(client)
    today = date.today()

    # Expenses spread across time: today, 5 days ago, 40 days ago, 200 days ago.
    _log_expense(client, student_id, 100.0, today, title="Today food")
    _log_expense(client, student_id, 50.0, today - timedelta(days=5), title="Five days ago")
    _log_expense(client, student_id, 200.0, today - timedelta(days=40), title="Forty days ago")
    _log_expense(client, student_id, 300.0, today - timedelta(days=200), title="Old expense")

    # Daily: 30 zero-filled buckets, today bucket has 100.
    daily = client.get(f"/api/analytics/{student_id}/trends?granularity=daily")
    assert daily.status_code == 200, daily.text
    d_data = daily.json()
    assert len(d_data) == 30
    assert d_data[0]["date"] == (today - timedelta(days=29)).isoformat()
    assert d_data[-1]["date"] == today.isoformat()
    assert all({"date", "label", "amount"} <= set(b) for b in d_data)
    today_bucket = [b for b in d_data if b["date"] == today.isoformat()][0]
    assert today_bucket["amount"] == 100.0
    # 40-day-old expense must NOT leak into daily window.
    assert sum(b["amount"] for b in d_data) == 150.0

    # Weekly: 12 buckets anchored Monday, includes 40-day-old expense.
    weekly = client.get(f"/api/analytics/{student_id}/trends?granularity=weekly")
    assert weekly.status_code == 200, weekly.text
    w_data = weekly.json()
    assert len(w_data) == 12
    for b in w_data:
        # Bucket start must be a Monday.
        assert date.fromisoformat(b["date"]).weekday() == 0
    assert sum(b["amount"] for b in w_data) == 350.0

    # Monthly: 12 buckets anchored on the 1st, includes all expenses.
    monthly = client.get(f"/api/analytics/{student_id}/trends?granularity=monthly")
    assert monthly.status_code == 200, monthly.text
    m_data = monthly.json()
    assert len(m_data) == 12
    for b in m_data:
        assert date.fromisoformat(b["date"]).day == 1
    assert sum(b["amount"] for b in m_data) == 650.0


def test_trends_empty_zero_filled(client):
    student_id = _register_student(client, name="Empty Trend", email="empty-trend@school.edu")
    for granularity, expected in (("daily", 30), ("weekly", 12), ("monthly", 12)):
        res = client.get(f"/api/analytics/{student_id}/trends?granularity={granularity}")
        assert res.status_code == 200, res.text
        data = res.json()
        assert len(data) == expected
        assert all(b["amount"] == 0.0 for b in data)


def test_trends_invalid_granularity_and_student(client):
    student_id = _register_student(client, name="Bad Trend", email="bad-trend@school.edu")
    bad = client.get(f"/api/analytics/{student_id}/trends?granularity=yearly")
    assert bad.status_code == 422
    missing = client.get("/api/analytics/999999/trends?granularity=daily")
    assert missing.status_code == 404


def test_trends_legacy_no_granularity(client):
    """Omitting granularity keeps the legacy current-month daily behavior."""
    student_id = _register_student(client, name="Legacy Trend", email="legacy-trend@school.edu")
    today = date.today()
    _log_expense(client, student_id, 75.0, today, title="Legacy today")
    res = client.get(f"/api/analytics/{student_id}/trends")
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data) >= 1
    assert sum(b["amount"] for b in data) == 75.0
