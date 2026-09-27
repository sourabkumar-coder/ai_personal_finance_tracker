"""Budget SMS alerts via TextBee — all HTTP mocked, zero live SMS spent."""

from datetime import date

from app.database.models import Budget, Expense, Student
from app.services.budget_service import BudgetService
from app.services.sms_service import SmsService
from app.utils.auth import get_password_hash


class _FakeResp:
    status_code = 200
    text = '{"ok": true}'


def _enable_sms(monkeypatch):
    monkeypatch.setenv("TEXTBEE_API_KEY", "test-key")
    monkeypatch.setenv("BUDGET_SMS_RECIPIENT", "+910000000000")
    monkeypatch.setenv("BUDGET_SMS_ENABLED", "true")
    monkeypatch.setenv("TEXTBEE_DRY_RUN", "false")
    monkeypatch.delenv("TEXTBEE_DEVICE_ID", raising=False)


def _mock_post(monkeypatch, calls):
    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return _FakeResp()

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)


def _make_student(db_session, email="sms@school.edu"):
    s = Student(
        name="Sms User", email=email, monthly_allowance=5000.0,
        hashed_password=get_password_hash("test-pass-123"),
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


def test_exceeded_sends_once_with_correct_payload(db_session, monkeypatch):
    _enable_sms(monkeypatch)
    calls = []
    _mock_post(monkeypatch, calls)
    s = _make_student(db_session)

    alert = {
        "is_exceeded": True, "is_warning": False, "category": "Food",
        "monthly_limit": 100.0, "total_spent": 120.0,
        "remaining": -20.0, "percentage_used": 120.0, "message": "x",
    }
    res = SmsService.maybe_send_budget_alert(db_session, s.id, alert)
    assert res == {"sent": True, "reason": "sent"}
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.textbee.dev/api/v1/gateway/send-sms"
    assert calls[0]["headers"]["x-api-key"] == "test-key"
    assert calls[0]["json"]["recipients"] == ["+910000000000"]
    assert "Food" in calls[0]["json"]["message"] and "EXCEEDED" in calls[0]["json"]["message"]

    # Same alert again this month -> suppressed, no second HTTP call.
    res2 = SmsService.maybe_send_budget_alert(db_session, s.id, alert)
    assert res2 == {"sent": False, "reason": "duplicate"}
    assert len(calls) == 1


def test_disabled_sends_nothing(db_session, monkeypatch):
    _enable_sms(monkeypatch)
    monkeypatch.setenv("BUDGET_SMS_ENABLED", "false")
    calls = []
    _mock_post(monkeypatch, calls)
    s = _make_student(db_session, email="sms-off@school.edu")

    alert = {
        "is_exceeded": True, "is_warning": False, "category": "Food",
        "monthly_limit": 100.0, "total_spent": 120.0,
        "remaining": -20.0, "percentage_used": 120.0, "message": "x",
    }
    assert SmsService.maybe_send_budget_alert(db_session, s.id, alert) == {
        "sent": False, "reason": "disabled",
    }
    assert calls == []


def test_expense_flow_sends_warning_then_exceeded_once_each(db_session, monkeypatch):
    """End-to-end through check_budget_exceeded: 90/100 warns, 110/100 exceeds."""
    _enable_sms(monkeypatch)
    calls = []
    _mock_post(monkeypatch, calls)
    s = _make_student(db_session, email="sms-flow@school.edu")
    today = date.today()
    db_session.add(Budget(
        student_id=s.id, category="Food", monthly_limit=100.0,
        month=today.month, year=today.year,
    ))
    db_session.commit()

    db_session.add(Expense(student_id=s.id, title="Lunch", amount=90.0, category="Food", date=today))
    db_session.commit()
    alert = BudgetService.check_budget_exceeded(db_session, s.id, "Food", today)
    assert alert and alert["is_warning"] and not alert["is_exceeded"]
    assert len(calls) == 1
    assert "90%" in calls[0]["json"]["message"]

    db_session.add(Expense(student_id=s.id, title="Dinner", amount=20.0, category="Food", date=today))
    db_session.commit()
    alert2 = BudgetService.check_budget_exceeded(db_session, s.id, "Food", today)
    assert alert2 and alert2["is_exceeded"]
    assert len(calls) == 2 and "EXCEEDED" in calls[1]["json"]["message"]

    # Third check at same level -> no further SMS.
    BudgetService.check_budget_exceeded(db_session, s.id, "Food", today)
    assert len(calls) == 2
