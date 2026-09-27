def test_income_deposit_20_percent_auto_savings(client):
    # 1. Register student
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Sarah Connor",
            "email": "sarah@cyber.edu",
            "monthly_allowance": 10000.0,
            "currency": "INR",
        },
    )
    assert reg.status_code == 201
    student_id = reg.json()["id"]

    # 2. Add an INCOME deposit of 5000 INR
    income_res = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Freelance Design Stipend",
            "amount": 5000.0,
            "category": "Income",
            "transaction_type": "INCOME",
            "payment_method": "UPI",
        },
    )
    assert income_res.status_code == 201
    data = income_res.json()
    assert data["transaction_type"] == "INCOME"
    assert "auto_savings_synced" in data
    assert data["auto_savings_synced"] is not None
    assert data["auto_savings_synced"]["synced_amount"] == 1000.0  # 20% of 5000

    # 3. Verify the goal received the 1000 INR deposit
    goals_res = client.get(f"/api/goals/{student_id}")
    assert goals_res.status_code == 200
    goals = goals_res.json()
    assert len(goals) >= 1
    matching_goal = next((g for g in goals if g["id"] == data["auto_savings_synced"]["goal_id"]), None)
    assert matching_goal is not None
    assert matching_goal["current_amount"] == 3000.0  # 2000 from monthly allowance (10000) + 1000 from income deposit (5000)
