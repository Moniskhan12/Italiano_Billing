from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_signup_login_and_me() -> None:
    email = f"alice+{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    r = client.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201

    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    tokens = r.json()
    access = tokens["access_token"]

    r = client.get("/auth/me")
    assert r.status_code == 401

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == email
