import uuid

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    password = "MosalaSecure123!"
    encoded = hash_password(password)

    assert encoded != password
    assert verify_password(password, encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "landlord")

    decoded_user_id, role = decode_access_token(token)

    assert decoded_user_id == user_id
    assert role == "landlord"
