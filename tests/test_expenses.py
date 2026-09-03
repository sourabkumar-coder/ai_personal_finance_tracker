def test_create_and_list_expenses(client):
    # 1. Register student
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alice Smith", "email": "alice@school.edu", "monthly_allowance": 500.0},
    )
    assert reg.status_code == 201
    student_id = reg.json()["id"]

    # 2. POST /api/expenses/ - Create an expense
    exp = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Calculus Book",
            "amount": 55.0,
            "category": "Books",
            "payment_method": "Card",
        },
    )
    assert exp.status_code == 201
    expense_data = exp.json()
    assert expense_data["id"] is not None
    assert expense_data["title"] == "Calculus Book"
    assert expense_data["amount"] == 55.0
    assert expense_data["category"] == "Books"

    # 3. GET /api/expenses/{student_id} - View all expenses for student
    res = client.get(f"/api/expenses/{student_id}")
    assert res.status_code == 200
    expenses = res.json()
    assert len(expenses) == 1
    assert expenses[0]["title"] == "Calculus Book"


def test_update_and_delete_expense(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "David", "email": "david@school.edu", "monthly_allowance": 300.0},
    )
    student_id = reg.json()["id"]

    exp = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Notebook",
            "amount": 10.0,
            "category": "Stationery",
        },
    )
    expense_id = exp.json()["id"]

    # UPDATE: PUT/PATCH /api/expenses/{expense_id}
    update_res = client.patch(
        f"/api/expenses/{expense_id}",
        json={"amount": 12.5, "notes": "Spiral bound"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 12.5
    assert update_res.json()["notes"] == "Spiral bound"

    # DELETE: DELETE /api/expenses/{expense_id}
    del_res = client.delete(f"/api/expenses/{expense_id}")
    assert del_res.status_code == 204

    # Verify student expenses list is now empty
    res = client.get(f"/api/expenses/{student_id}")
    assert len(res.json()) == 0
