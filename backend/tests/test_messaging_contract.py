import pytest
from pydantic import ValidationError

from app.schemas.messaging import MessageCreate


def test_message_body_is_trimmed():
    message = MessageCreate(body="  Is electricity included?  ")
    assert message.body == "Is electricity included?"


def test_message_body_cannot_be_blank():
    with pytest.raises(ValidationError):
        MessageCreate(body="   ")


def test_message_body_is_bounded():
    with pytest.raises(ValidationError):
        MessageCreate(body="x" * 2001)
