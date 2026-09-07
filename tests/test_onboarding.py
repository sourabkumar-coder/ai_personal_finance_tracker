def test_register_student(client):
    response = client.post(
        "/api/onboarding/register",
        json={
            "name": "Sarah Connor",
            "email": "sarah@university.edu",
            "monthly_allowance": 600.0,
            "currency": "INR",
            "college_year": "Junior",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sarah Connor"
    assert data["email"] == "sarah@university.edu"
    assert data["monthly_allowance"] == 600.0
    assert "id" in data


def test_register_duplicate_email_case_insensitive(client):
    client.post(
        "/api/onboarding/register",
        json={
            "name": "John Doe",
            "email": "john.doe@university.edu",
            "monthly_allowance": 500.0,
        },
    )
    # Attempt registering with same email in uppercase
    dup = client.post(
        "/api/onboarding/register",
        json={
            "name": "Johnny",
            "email": "JOHN.DOE@UNIVERSITY.EDU",
            "monthly_allowance": 400.0,
        },
    )
    assert dup.status_code == 400
    assert "already registered" in dup.json()["detail"].lower()


def test_get_student_profile(client):
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Peter Parker",
            "email": "peter@dailybugle.com",
            "monthly_allowance": 450.0,
            "currency": "USD",
        },
    )
    student_id = reg.json()["id"]

    response = client.get(f"/api/onboarding/profile/{student_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Peter Parker"


def test_get_student_profile_not_found(client):
    response = client.get("/api/onboarding/profile/9999")
    assert response.status_code == 404


def test_get_student_by_email(client):
    client.post(
        "/api/onboarding/register",
        json={
            "name": "Clark Kent",
            "email": "clark@planet.com",
            "monthly_allowance": 800.0,
        },
    )
    res = client.get("/api/onboarding/profile/by-email/CLARK@planet.com")
    assert res.status_code == 200
    assert res.json()["name"] == "Clark Kent"


def test_update_student_profile_put_and_patch(client):
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Bruce Wayne",
            "email": "bruce@gotham.edu",
            "monthly_allowance": 1000.0,
        },
    )
    student_id = reg.json()["id"]

    # Test PUT update
    put_res = client.put(
        f"/api/onboarding/profile/{student_id}",
        json={"monthly_allowance": 1200.0, "name": "Bruce Wayne Jr."},
    )
    assert put_res.status_code == 200
    assert put_res.json()["monthly_allowance"] == 1200.0
    assert put_res.json()["name"] == "Bruce Wayne Jr."

    # Test PATCH update
    patch_res = client.patch(
        f"/api/onboarding/profile/{student_id}",
        json={"currency": "EUR"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["currency"] == "EUR"


def test_update_student_email_conflict(client):
    # Register user 1
    client.post(
        "/api/onboarding/register",
        json={"name": "User 1", "email": "user1@domain.com", "monthly_allowance": 100.0},
    )
    # Register user 2
    r2 = client.post(
        "/api/onboarding/register",
        json={"name": "User 2", "email": "user2@domain.com", "monthly_allowance": 200.0},
    )
    id2 = r2.json()["id"]

    # Try to change user 2's email to user 1's email
    conflict_res = client.patch(
        f"/api/onboarding/profile/{id2}",
        json={"email": "user1@domain.com"},
    )
    assert conflict_res.status_code == 400
    assert "already in use" in conflict_res.json()["detail"].lower()


def test_list_and_delete_student(client):
    reg = client.post(
        "/api/onboarding/register",
        json={"name": "Barry Allen", "email": "barry@star.edu", "monthly_allowance": 300.0},
    )
    student_id = reg.json()["id"]

    # List
    list_res = client.get("/api/onboarding/students")
    assert list_res.status_code == 200
    assert any(s["id"] == student_id for s in list_res.json())

    # Delete
    del_res = client.delete(f"/api/onboarding/profile/{student_id}")
    assert del_res.status_code == 204

    # Verify 404 after delete
    get_res = client.get(f"/api/onboarding/profile/{student_id}")
    assert get_res.status_code == 404
