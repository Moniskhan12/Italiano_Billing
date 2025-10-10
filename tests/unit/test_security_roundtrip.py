from app.security import hash_password, verify_password


def test_argon2_roundtrip() -> None:
    raw = "secret123"
    h = hash_password(raw)
    assert verify_password(raw, h)
