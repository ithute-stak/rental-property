from app.schemas.property import PropertyRead, PublicPropertyRead


def test_public_property_contract_hides_exact_location_and_owner():
    public_fields = PublicPropertyRead.model_fields

    assert "physical_address" not in public_fields
    assert "latitude" not in public_fields
    assert "longitude" not in public_fields
    assert "owner_id" not in public_fields


def test_internal_property_contract_keeps_exact_location_for_authorized_workflows():
    internal_fields = PropertyRead.model_fields

    assert "physical_address" in internal_fields
    assert "latitude" in internal_fields
    assert "longitude" in internal_fields
    assert "owner_id" in internal_fields
