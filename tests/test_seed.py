def test_seed_demo_student(client):
    response = client.post("/api/onboarding/seed-demo")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Alex Rivera"
    assert data["email"] == "alex.rivera@campus.edu"
    assert data["monthly_allowance"] == 850.0
    student_id = data["id"]

    # Verify expenses were seeded
    exp_res = client.get(f"/api/expenses/{student_id}")
    assert exp_res.status_code == 200
    assert len(exp_res.json()) >= 5

    # Verify budgets were seeded
    bud_res = client.get(f"/api/budgets/{student_id}")
    assert bud_res.status_code == 200
    assert len(bud_res.json()) >= 3

    # Verify budget status computed
    status_res = client.get(f"/api/budgets/{student_id}/status")
    assert status_res.status_code == 200
    assert len(status_res.json()) >= 3

    # Verify goals were seeded
    goal_res = client.get(f"/api/goals/{student_id}")
    assert goal_res.status_code == 200
    assert len(goal_res.json()) >= 2

    # Verify recommendations exist
    rec_res = client.get(f"/api/recommendations/{student_id}")
    assert rec_res.status_code == 200
    assert len(rec_res.json()) >= 1

    # Verify re-seeding resets cleanly
    reseed_res = client.post("/api/onboarding/seed-demo")
    assert reseed_res.status_code == 200
    assert reseed_res.json()["email"] == "alex.rivera@campus.edu"
