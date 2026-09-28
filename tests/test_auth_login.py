"""Login edge cases: legacy password-less accounts + token lifetime."""

from datetime import datetime, timezone

from jose import jwt

from app.config import settings
from app.database.models import Student
from app.utils.auth import get_password_hash


def _legacy_student(db_session, email="legacy@school.edu"):
    s = Student(name="Legacy", email=email, monthly_allowance=1000.0, hashed_password="")
    db_session.add(s)
    db_session.commit()
    return s


def test_legacy_account_gets_clear_message_not_500(client, db_session):
    _legacy_student(db_session)
    res = client.post(
        "/api/auth/login", data={"username": "legacy@school.edu", "password": "anything"}
    )
    assert res.status_code == 401
    assert "before passwords" in res.json()["detail"]


def test_login_token_lasts_24h_per_config(client):
    reg = client.post("/api/auth/register", json={
        "name": "Ttl User", "email": "ttl@school.edu",
        "password": "secret123", "monthly_allowance": 500.0,
    })
    assert reg.status_code == 201
    login = client.post(
        "/api/auth/login", data={"username": "ttl@school.edu", "password": "secret123"}
    )
    assert login.status_code == 200
    payload = jwt.decode(
        login.json()["access_token"], settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    ttl_hours = (
        datetime.fromtimestamp(payload["exp"], tz=timezone.utc) - datetime.now(timezone.utc)
    ).total_seconds() / 3600
    assert 23.0 < ttl_hours <= 24.0
