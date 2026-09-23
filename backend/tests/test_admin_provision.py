import pytest

from app.provision_admin import validate_admin_inputs


def test_admin_provision_requires_supported_password_length():
    with pytest.raises(ValueError, match="8 characters"):
        validate_admin_inputs("59000000", "Mosala Admin", "short")


def test_admin_provision_normalizes_basic_identity_fields():
    phone, name = validate_admin_inputs(
        " 59000000 ",
        " Mosala Admin ",
        "StrongAdminPass123!",
    )

    assert phone == "59000000"
    assert name == "Mosala Admin"


def test_admin_provision_allows_email_only_identity():
    phone, name = validate_admin_inputs(
        None,
        " Mosala Admin ",
        "Bootstrap9!",
    )

    assert phone is None
    assert name == "Mosala Admin"
