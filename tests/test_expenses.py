def test_create_and_list_expenses(client):
    # Register student
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Alice Smith", "email": "alice@school.edu", "monthly_allowance": 500.0},
    )
    student_id = reg.json()["id"]

    # Add expense
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
    assert expense_data["title"] == "Calculus Book"
    assert expense_data["amount"] == 55.0

    # List expenses
    res = client.get(f"/api/expenses/{student_id}")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_update_and_get_single_expense(client):
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

    # Get single item
    item_res = client.get(f"/api/expenses/item/{expense_id}")
    assert item_res.status_code == 200
    assert item_res.json()["title"] == "Notebook"

    # Update expense
    update_res = client.patch(
        f"/api/expenses/{expense_id}",
        json={"amount": 12.5, "notes": "Spiral bound"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 12.5
    assert update_res.json()["notes"] == "Spiral bound"


def test_delete_expense(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Bob Lee", "email": "bob@school.edu", "monthly_allowance": 400.0},
    )
    student_id = reg.json()["id"]

    exp = client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Coffee",
            "amount": 4.5,
            "category": "Food",
            "payment_method": "UPI",
        },
    )
    expense_id = exp.json()["id"]

    del_res = client.delete(f"/api/expenses/{expense_id}")
    assert del_res.status_code == 204

    # Verify empty list
    res = client.get(f"/api/expenses/{student_id}")
    assert len(res.json()) == 0
