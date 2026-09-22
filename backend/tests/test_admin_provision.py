import pytest

from app.provision_admin import validate_admin_inputs


def test_admin_provision_requires_strong_password():
    with pytest.raises(ValueError, match="12 characters"):
        validate_admin_inputs("59000000", "Mosala Admin", "shortpass")


def test_admin_provision_normalizes_basic_identity_fields():
    phone, name = validate_admin_inputs(
        " 59000000 ",
        " Mosala Admin ",
        "StrongAdminPass123!",
    )

    assert phone == "59000000"
    assert name == "Mosala Admin"
