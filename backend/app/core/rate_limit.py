import hashlib

from redis.asyncio import Redis

_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


def rate_limit_key(namespace: str, identity: str) -> str:
    digest = hashlib.sha256(identity.strip().lower().encode("utf-8")).hexdigest()
    return f"mosala:rate:{namespace}:{digest}"


async def consume_rate_limit(
    redis: Redis,
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    current, ttl = await redis.eval(
        _RATE_LIMIT_SCRIPT,
        1,
        key,
        window_seconds,
    )
    retry_after = max(int(ttl), 1)
    return int(current) <= limit, retry_after
