def test_recommendation_and_forecast_flow(client):
    # Register student
    reg = client.post(
        "/api/onboarding/register",
        json={
            "name": "Bruce Banner",
            "email": "bruce@lab.edu",
            "monthly_allowance": 1000.0,
        },
    )
    student_id = reg.json()["id"]

    # Initial welcome recommendation should exist
    recs_res = client.get(f"/api/recommendations/{student_id}")
    assert recs_res.status_code == 200
    initial_recs = recs_res.json()
    assert len(initial_recs) >= 1

    # Log expense
    client.post(
        "/api/expenses/",
        json={
            "student_id": student_id,
            "title": "Lab equipment",
            "amount": 800.0,
            "category": "Education",
        },
    )

    # Generate recommendations
    gen_res = client.post(f"/api/recommendations/{student_id}/generate")
    assert gen_res.status_code == 200
    recs = gen_res.json()
    assert len(recs) >= 1
    # 800 out of 1000 is 80% (>75%), so High Burn Rate alert should trigger
    assert any("Burn Rate" in r["title"] for r in recs)

    # Test marking recommendation as read
    rec_id = recs[0]["id"]
    read_res = client.patch(f"/api/recommendations/{rec_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Test unread_only filter
    unread_res = client.get(f"/api/recommendations/{student_id}?unread_only=true")
    assert unread_res.status_code == 200
    assert all(r["is_read"] is False for r in unread_res.json())

    # Test mark-all-as-read
    read_all_res = client.patch(f"/api/recommendations/{student_id}/read-all")
    assert read_all_res.status_code == 200
    assert read_all_res.json()["status"] == "success"

    # Test deleting a recommendation
    del_res = client.delete(f"/api/recommendations/{rec_id}")
    assert del_res.status_code == 204

    # Test forecast endpoint
    forecast_res = client.get(f"/api/recommendations/{student_id}/forecast")
    assert forecast_res.status_code == 200
    forecast = forecast_res.json()
    assert "daily_burn_rate" in forecast
    assert "projected_month_end_spent" in forecast
    assert forecast["current_spent"] == 800.0


def test_recommendation_student_not_found(client):
    res = client.get("/api/recommendations/9999")
    assert res.status_code == 404
