import pytest

from app.core.rate_limit import consume_rate_limit, rate_limit_key


class _FakeRedis:
    def __init__(self, current: int, ttl: int):
        self.current = current
        self.ttl = ttl

    async def eval(self, *_args):
        return [self.current, self.ttl]


def test_rate_limit_key_does_not_expose_login_identifier():
    identifier = "person@example.com"
    key = rate_limit_key("login", identifier)

    assert key.startswith("mosala:rate:login:")
    assert identifier not in key
    assert rate_limit_key("login", identifier.upper()) == key


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_threshold():
    allowed, retry_after = await consume_rate_limit(
        _FakeRedis(current=11, ttl=42),
        key="test",
        limit=10,
        window_seconds=300,
    )

    assert allowed is False
    assert retry_after == 42


@pytest.mark.asyncio
async def test_rate_limit_allows_attempts_within_threshold():
    allowed, retry_after = await consume_rate_limit(
        _FakeRedis(current=10, ttl=100),
        key="test",
        limit=10,
        window_seconds=300,
    )

    assert allowed is True
    assert retry_after == 100
