def test_register_student(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "New Student",
            "email": "new@college.edu",
            "password": "securepassword",
            "monthly_allowance": 500.0,
            "currency": "INR",
            "college_year": "Freshman"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["student"]["email"] == "new@college.edu"

def test_login_student(client, test_student):
    response = client.post(
        "/api/auth/login",
        data={
            "username": "test@college.edu",
            "password": "testpassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_student_wrong_password(client, test_student):
    response = client.post(
        "/api/auth/login",
        data={
            "username": "test@college.edu",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_get_me(authed_client, test_student):
    response = authed_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@college.edu"

def test_protected_route_without_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
