def test_register_student(client):
    response = client.post(
        "/api/onboarding/register",
        json={
            "name": "Sarah Connor",
            "email": "sarah@university.edu",
            "monthly_allowance": 600.0,
            "currency": "USD",
            "college_year": "Junior",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sarah Connor"
    assert data["email"] == "sarah@university.edu"
    assert data["monthly_allowance"] == 600.0
    assert "id" in data


def test_get_student_profile(client):
    # Register first
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "John Doe",
            "email": "john@university.edu",
            "monthly_allowance": 450.0,
            "currency": "USD",
        },
    )
    student_id = reg.json()["id"]

    response = client.get(f"/api/onboarding/profile/{student_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "John Doe"


def test_update_student_profile(client):
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Bruce Wayne",
            "email": "bruce@university.edu",
            "monthly_allowance": 1000.0,
        },
    )
    student_id = reg.json()["id"]

    response = client.put(
        f"/api/onboarding/profile/{student_id}",
        json={"monthly_allowance": 1200.0},
    )
    assert response.status_code == 200
    assert response.json()["monthly_allowance"] == 1200.0
