import uuid

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
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


def test_refresh_tokens_are_random_and_only_hashes_need_persistence():
    first = create_refresh_token()
    second = create_refresh_token()

    assert first != second
    assert len(first) >= 64
    assert len(hash_refresh_token(first)) == 64
    assert hash_refresh_token(first) != first
    assert hash_refresh_token(first) == hash_refresh_token(first)
