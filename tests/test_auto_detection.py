import pytest
from app.ai.transaction_parser import TransactionParser
from app.ai.transaction_categorizer import TransactionCategorizer
from app.services.deduplication_service import DeduplicationService
from app.config import settings


@pytest.fixture
def student_id(client):
    """Helper fixture to create a test student."""
    res = client.post(
        "/api/onboarding/register",
        json={
            "name": "Aryan Sharma",
            "email": "aryan@campus.edu",
            "monthly_allowance": 8000.0,
            "currency": "INR",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


# =========================================================================
# Unit Tests for Parser Cases (Section 31 of Requirements)
# =========================================================================

def test_case_1_zomato_payment():
    """Case 1: 'Payment of ₹350 to Zomato successful' -> Expense, ₹350, Zomato, Food, SUCCESS"""
    parsed = TransactionParser.parse_notification("Payment of ₹350 to Zomato successful", title="PhonePe")
    assert parsed["is_valid_transaction"] is True
    assert parsed["amount"] == 350.0
    assert "zomato" in parsed["merchant"].lower()
    assert parsed["transaction_type"] == "EXPENSE"
    assert parsed["status"] == "SUCCESS"

    cat = TransactionCategorizer.categorize(parsed["merchant"], parsed["amount"])
    assert cat["category"] == "Food"


def test_case_2_amazon_payment():
    """Case 2: 'You paid ₹1200 to Amazon' -> Expense, ₹1200, Amazon, Shopping"""
    parsed = TransactionParser.parse_notification("You paid ₹1200 to Amazon", title="Google Pay")
    assert parsed["is_valid_transaction"] is True
    assert parsed["amount"] == 1200.0
    assert "amazon" in parsed["merchant"].lower()
    assert parsed["transaction_type"] == "EXPENSE"

    cat = TransactionCategorizer.categorize(parsed["merchant"], parsed["amount"])
    assert cat["category"] == "Shopping"


def test_case_3_income_received():
    """Case 3: '₹500 received from Rahul' -> Income, ₹500, Rahul"""
    parsed = TransactionParser.parse_notification("₹500 received from Rahul", title="Paytm")
    assert parsed["is_valid_transaction"] is True
    assert parsed["amount"] == 500.0
    assert "rahul" in parsed["merchant"].lower()
    assert parsed["transaction_type"] == "INCOME"
    assert parsed["status"] == "SUCCESS"


def test_case_4_failed_payment_ignored():
    """Case 4: 'Your payment of ₹800 failed' -> IGNORE"""
    parsed = TransactionParser.parse_notification("Your payment of ₹800 failed", title="PhonePe")
    assert parsed["is_valid_transaction"] is False
    assert parsed["status"] == "FAILED"
    assert "not successful" in parsed["rejection_reason"]


def test_case_5_balance_alert_ignored():
    """Case 5: 'Your account balance is ₹8,450' -> IGNORE"""
    parsed = TransactionParser.parse_notification("Your account balance is ₹8,450", title="HDFC Bank")
    assert parsed["is_valid_transaction"] is False
    assert "non-transaction pattern" in parsed["rejection_reason"].lower()


def test_case_6_social_notification_ignored():
    """Case 6: 'Instagram: Rahul posted a story' -> IGNORE"""
    parsed = TransactionParser.parse_notification(
        "Rahul posted a story",
        title="Instagram",
        package_name="com.instagram.android",
    )
    assert parsed["is_valid_transaction"] is False


def test_case_8_unknown_notification_no_fake_transaction():
    """Case 8: Unknown notification format -> No fake transaction"""
    parsed = TransactionParser.parse_notification("Hey, what are you doing tonight?", title="WhatsApp")
    assert parsed["is_valid_transaction"] is False
    assert parsed["amount"] is None


# =========================================================================
# API Integration Tests for Auto-Detection Endpoints
# =========================================================================

def test_api_auto_detect_valid_payment(client, student_id, monkeypatch):
    """End-to-end API test: simulate valid notification and verify expense created."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    res = client.post(
        "/api/transactions/simulate-notification",
        json={
            "student_id": student_id,
            "notification_text": "Payment of ₹350 to Zomato successful",
            "source_app": "PhonePe",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["is_duplicate"] is False
    assert data["expense"]["amount"] == 350.0
    assert "Zomato" in data["expense"]["merchant"]
    assert data["expense"]["category"] == "Food"
    assert data["expense"]["is_automatically_detected"] is True
    assert data["expense"]["source_app"] == "PhonePe"


def test_case_7_duplicate_prevention(client, student_id, monkeypatch):
    """Case 7: Two identical payment notifications -> Exactly ONE transaction saved."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    payload = {
        "student_id": student_id,
        "notification_text": "Paid ₹220 to Uber via UPI Ref 987654321012",
        "source_app": "Google Pay",
    }

    # First notification
    res1 = client.post("/api/transactions/simulate-notification", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["is_duplicate"] is False
    exp_id_1 = data1["expense"]["id"]

    # Second duplicate notification
    res2 = client.post("/api/transactions/simulate-notification", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["success"] is True
    assert data2["is_duplicate"] is True
    # Verify same expense returned and no duplicate created
    assert data2["expense"]["id"] == exp_id_1

    # Verify student expenses count increased by only 1
    exp_list = client.get(f"/api/expenses/{student_id}").json()
    uber_expenses = [e for e in exp_list if "uber" in (e.get("merchant") or e.get("title") or "").lower()]
    assert len(uber_expenses) == 1


def test_api_failed_notification_rejection(client, student_id):
    """Failed payment notification should not create an expense."""
    res = client.post(
        "/api/transactions/simulate-notification",
        json={
            "student_id": student_id,
            "notification_text": "Your payment of ₹800 failed",
            "source_app": "PhonePe",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["ignored"] is True
    assert data["expense"] is None


def test_personalized_ai_learning(client, student_id, monkeypatch):
    """
    Section 14: User corrections (e.g. Amazon -> Education) must be saved
    and applied to future transactions.
    """
    monkeypatch.setattr(settings, "gemini_api_key", "")

    # 1. First transaction: Amazon defaults to Shopping
    res1 = client.post(
        "/api/transactions/simulate-notification",
        json={
            "student_id": student_id,
            "notification_text": "You paid ₹1200 to Amazon",
            "source_app": "Google Pay",
        },
    )
    assert res1.status_code == 200
    exp1 = res1.json()["expense"]
    assert exp1["category"] == "Shopping"

    # 2. User confirms/corrects category to Education with preference saving
    conf_res = client.patch(
        f"/api/transactions/{exp1['id']}/confirm",
        json={
            "category": "Education",
            "subcategory": "College Books",
            "save_as_preference": True,
        },
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["category"] == "Education"

    # 3. Future transaction for Amazon should automatically be categorized as Education!
    res2 = client.post(
        "/api/transactions/simulate-notification",
        json={
            "student_id": student_id,
            "notification_text": "You paid ₹450 to Amazon for textbook",
            "source_app": "Google Pay",
        },
    )
    assert res2.status_code == 200
    exp2 = res2.json()["expense"]
    assert exp2["category"] == "Education"
    assert exp2["confidence"] == 1.0


def test_tracking_status_and_settings(client, student_id):
    """Verify tracking status endpoint and toggling settings."""
    # Check initial status
    status_res = client.get(f"/api/transactions/{student_id}/status")
    assert status_res.status_code == 200
    stat = status_res.json()
    assert stat["auto_tracking_enabled"] is True
    assert "Google Pay" in stat["supported_apps"]

    # Toggle tracking OFF
    upd_res = client.put(
        f"/api/transactions/{student_id}/settings",
        json={"auto_tracking_enabled": False},
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["auto_tracking_enabled"] is False

    # Attempt auto-detection when disabled
    attempt_res = client.post(
        "/api/transactions/simulate-notification",
        json={
            "student_id": student_id,
            "notification_text": "Payment of ₹150 to CCD successful",
        },
    )
    assert attempt_res.status_code == 200
    assert attempt_res.json()["ignored"] is True
    assert "disabled" in attempt_res.json()["message"].lower()
