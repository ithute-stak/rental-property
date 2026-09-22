import uuid

import pytest

from app.core.storage import storage


def test_property_upload_key_is_scoped_to_property():
    property_id = uuid.uuid4()
    object_key, upload_url = storage.create_property_upload(property_id, "image/webp")

    assert object_key.startswith(f"properties/{property_id}/")
    assert object_key.endswith(".webp")
    assert "http://localhost:9000" in upload_url


def test_unsupported_media_type_is_rejected_before_upload():
    with pytest.raises(ValueError):
        storage.create_property_upload(uuid.uuid4(), "application/pdf")
