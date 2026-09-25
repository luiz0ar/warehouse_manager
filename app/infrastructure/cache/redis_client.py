import asyncio

import redis.asyncio as aioredis

from app.core.config import settings

_redis_clients: dict[asyncio.AbstractEventLoop, aioredis.Redis] = {}


async def get_redis_client() -> aioredis.Redis:
    """Return an asynchronous Redis client instance bound to the active event loop."""
    loop = asyncio.get_running_loop()
    if loop not in _redis_clients:
        _redis_clients[loop] = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_clients[loop]


async def close_redis_client() -> None:
    """Close all open Redis client connections."""
    for client in list(_redis_clients.values()):
        await client.aclose()
    _redis_clients.clear()