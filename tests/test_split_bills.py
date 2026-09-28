from datetime import date


def test_create_group_and_members(client):
    # 1. Register student
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex@college.edu", "monthly_allowance": 10000.0},
    )
    assert reg.status_code == 201
    student_id = reg.json()["id"]

    # 2. Create Split Group with initial members
    grp_resp = client.post(
        "/api/split-bills/groups",
        json={
            "student_id": student_id,
            "name": "Flat 204 Roommates",
            "description": "Monthly rent and shared food",
            "initial_members": [
                {"name": "Rohan Sharma", "email": "rohan@college.edu", "upi_id": "rohan@upi"},
                {"name": "Sneha Roy", "upi_id": "sneha@upi"},
            ],
        },
    )
    assert grp_resp.status_code == 201
    group_data = grp_resp.json()
    assert group_data["name"] == "Flat 204 Roommates"
    assert len(group_data["members"]) == 2
    group_id = group_data["id"]

    # 3. Add an additional member
    add_mem = client.post(
        f"/api/split-bills/groups/{group_id}/members",
        json={"name": "Vikram Singh", "email": "vikram@college.edu"},
    )
    assert add_mem.status_code == 201
    assert add_mem.json()["name"] == "Vikram Singh"

    # 4. Fetch group details
    details = client.get(f"/api/split-bills/groups/{group_id}/details")
    assert details.status_code == 200
    assert len(details.json()["members"]) == 3


def test_create_equal_split_bill_with_expense_sync(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    grp_resp = client.post(
        "/api/split-bills/groups",
        json={
            "student_id": student_id,
            "name": "Weekend Trip",
            "initial_members": [
                {"name": "Rohan Sharma"},
                {"name": "Sneha Roy"},
            ],
        },
    )
    group_id = grp_resp.json()["id"]

    # Create an equal split bill of ₹1,200 between "You", "Rohan Sharma", and "Sneha Roy"
    bill_resp = client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "group_id": group_id,
            "title": "Highway Dhaba Dinner",
            "total_amount": 1200.0,
            "category": "Food",
            "payer_name": "You",
            "split_type": "EQUAL",
            "sync_to_expenses": True,
            "shares": [
                {"member_name": "You"},
                {"member_name": "Rohan Sharma"},
                {"member_name": "Sneha Roy"},
            ],
        },
    )
    assert bill_resp.status_code == 201
    b_data = bill_resp.json()
    assert b_data["total_amount"] == 1200.0
    assert len(b_data["shares"]) == 3
    assert b_data["your_share"] == 400.0
    assert b_data["your_net_impact"] == 800.0  # Others owe you ₹800
    assert b_data["synced_expense_id"] is not None

    # Verify auto-synced personal expense exists in user's expense tracker
    exp_res = client.get(f"/api/expenses/{student_id}")
    assert exp_res.status_code == 200
    expenses = exp_res.json()
    assert len(expenses) == 1
    assert expenses[0]["amount"] == 400.0
    assert "[Split]" in expenses[0]["title"]


def test_exact_split_bill_and_validation(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    # 1. Test mismatched sum failure
    bad_bill = client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Grocery Run",
            "total_amount": 500.0,
            "category": "Food",
            "payer_name": "You",
            "split_type": "EXACT",
            "shares": [
                {"member_name": "You", "share_amount": 200.0},
                {"member_name": "Rohan", "share_amount": 100.0},  # sum is 300, not 500
            ],
        },
    )
    assert bad_bill.status_code == 400

    # 2. Test valid exact split
    good_bill = client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Grocery Run",
            "total_amount": 500.0,
            "category": "Food",
            "payer_name": "You",
            "split_type": "EXACT",
            "shares": [
                {"member_name": "You", "share_amount": 200.0},
                {"member_name": "Rohan", "share_amount": 300.0},
            ],
        },
    )
    assert good_bill.status_code == 201
    assert good_bill.json()["your_share"] == 200.0


def test_balances_and_settlement_flow(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    # Bill 1: Alex ("You") pays ₹600 for Alex and Aman (₹300 each) -> Aman owes Alex ₹300
    client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Canteen Lunch",
            "total_amount": 600.0,
            "category": "Food",
            "payer_name": "You",
            "split_type": "EQUAL",
            "shares": [
                {"member_name": "You"},
                {"member_name": "Aman"},
            ],
        },
    )

    # Check balance
    bal_res1 = client.get(f"/api/split-bills/balances/{student_id}")
    assert bal_res1.status_code == 200
    b1 = bal_res1.json()
    assert b1["total_owed_to_you"] == 300.0
    assert b1["total_you_owe"] == 0.0
    assert b1["friends"][0]["name"] == "Aman"
    assert b1["friends"][0]["net_balance"] == 300.0
    assert b1["friends"][0]["status"] == "OWED_TO_YOU"

    # Bill 2: Aman pays ₹200 for Alex and Aman (₹100 each) -> Alex owes Aman ₹100
    client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Coffee",
            "total_amount": 200.0,
            "category": "Food",
            "payer_name": "Aman",
            "split_type": "EQUAL",
            "shares": [
                {"member_name": "You"},
                {"member_name": "Aman"},
            ],
        },
    )

    # Net balance: Aman owes 300 - 100 = ₹200
    bal_res2 = client.get(f"/api/split-bills/balances/{student_id}")
    b2 = bal_res2.json()
    assert b2["total_owed_to_you"] == 200.0
    assert b2["total_you_owe"] == 0.0
    assert b2["friends"][0]["net_balance"] == 200.0

    # Settle up: Aman pays Alex ₹200 via UPI
    settle_res = client.post(
        "/api/split-bills/settle",
        json={
            "student_id": student_id,
            "from_name": "Aman",
            "to_name": "You",
            "amount": 200.0,
            "payment_method": "UPI",
            "notes": "Paid via Google Pay",
        },
    )
    assert settle_res.status_code == 201

    # Check balance after settlement: net balance should now be 0.0 (SETTLED)
    bal_res3 = client.get(f"/api/split-bills/balances/{student_id}")
    b3 = bal_res3.json()
    assert b3["total_owed_to_you"] == 0.0
    assert b3["total_you_owe"] == 0.0
    assert b3["friends"][0]["status"] == "SETTLED"

    # Check settlements list
    settles_list = client.get(f"/api/split-bills/settlements/{student_id}")
    assert settles_list.status_code == 200
    assert len(settles_list.json()) == 1
    assert settles_list.json()[0]["amount"] == 200.0


def test_delete_split_bill_cleans_expense(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    bill_res = client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Movie Tickets",
            "total_amount": 800.0,
            "category": "Entertainment",
            "payer_name": "You",
            "split_type": "EQUAL",
            "sync_to_expenses": True,
            "shares": [
                {"member_name": "You"},
                {"member_name": "Pooja"},
            ],
        },
    )
    bill_id = bill_res.json()["id"]

    # Verify expense was synced
    exp_before = client.get(f"/api/expenses/{student_id}").json()
    assert len(exp_before) == 1

    # Delete split bill
    del_res = client.delete(f"/api/split-bills/bills/{bill_id}?student_id={student_id}")
    assert del_res.status_code == 204

    # Verify synced expense was also removed
    exp_after = client.get(f"/api/expenses/{student_id}").json()
    assert len(exp_after) == 0


def test_delete_settlement(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex_set@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    # Record settlement
    settle_res = client.post(
        "/api/split-bills/settle",
        json={
            "student_id": student_id,
            "from_name": "Rohan",
            "to_name": "You",
            "amount": 250.0,
            "payment_method": "UPI",
            "notes": "Testing settle delete",
        },
    )
    assert settle_res.status_code == 201
    settle_id = settle_res.json()["id"]

    # Delete settlement
    del_res = client.delete(f"/api/split-bills/settlements/{settle_id}?student_id={student_id}")
    assert del_res.status_code == 204

    # Verify list is empty
    lst = client.get(f"/api/split-bills/settlements/{student_id}").json()
    assert len(lst) == 0


def test_case_insensitive_friend_balances(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alex Rivera", "email": "alex_case@college.edu", "monthly_allowance": 10000.0},
    )
    student_id = reg.json()["id"]

    # Bill with "Rohan Sharma"
    client.post(
        "/api/split-bills/bills",
        json={
            "student_id": student_id,
            "title": "Dinner",
            "total_amount": 600.0,
            "payer_name": "You",
            "split_type": "EQUAL",
            "shares": [
                {"member_name": "You"},
                {"member_name": "Rohan Sharma"},
            ],
        },
    )

    # Settle with "rohan sharma" (lowercase)
    client.post(
        "/api/split-bills/settle",
        json={
            "student_id": student_id,
            "from_name": "rohan sharma",
            "to_name": "You",
            "amount": 300.0,
            "payment_method": "UPI",
        },
    )

    bal_res = client.get(f"/api/split-bills/balances/{student_id}")
    assert bal_res.status_code == 200
    b = bal_res.json()
    assert b["total_owed_to_you"] == 0.0
    assert b["total_you_owe"] == 0.0
    assert b["friends"][0]["status"] == "SETTLED"

