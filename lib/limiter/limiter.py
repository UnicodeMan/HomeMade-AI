import redis.asyncio
import asyncio
import os
from typing import Tuple

class RateLimiter:
    def __init__(self):
        self.redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}"
        self.redis = None

    async def init_redis(self):
        """Initialize Redis connection."""
        if self.redis is None:
            self.redis = await redis.asyncio.Redis.from_url(self.redis_url)

    async def close_redis(self):
        """Close Redis connection."""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()

    async def check_and_update_limit(self, client_key: str, limit: int, period: int) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded and update counter atomically.
        
        Args:
            client_key (str): The unique key for the client
            limit (int): Maximum number of allowed requests
            period (int): Time window in seconds
        """
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")

        key = f"rate_limit:{client_key}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            try:
                # Get current state
                await pipe.get(key)
                await pipe.ttl(key)
                current_count, ttl = await pipe.execute()
                
                # If TTL is -2 (key doesn't exist) or -1 (no expiry), treat as new key
                if ttl < 0:
                    await pipe.set(key, 1)
                    await pipe.expire(key, period)
                    await pipe.execute()
                    return False, 0
                
                current_count = int(current_count)
                if current_count >= limit:
                    return True, ttl
                
                # Increment counter while preserving TTL
                await pipe.incr(key)
                await pipe.execute()
                return False, 0
                
            except redis.RedisError as e:
                print(f"Redis error: {e}")
                return False, 0

    async def enforce_limit(self, client_key: str, limit: int, period: int, poll_interval: float = 0.5):
        """
        Enforce the rate limit for a client. Blocks until the limit is lifted.
        """
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")

        key = f"rate_limit:{client_key}"

        while True:
            async with self.redis.pipeline(transaction=True) as pipe:
                await pipe.get(key)
                await pipe.ttl(key)
                current_count, ttl = await pipe.execute()
                
                # If key expired or doesn't exist, allow immediately
                if ttl < 0:
                    await pipe.set(key, 1)
                    await pipe.expire(key, period)
                    await pipe.execute()
                    return
                
                current_count = int(current_count) if current_count else 0
                if current_count < limit:
                    await pipe.incr(key)
                    await pipe.execute()
                    return
                    
                print(f"Rate limit exceeded. Waiting {ttl} seconds")
                await asyncio.sleep(poll_interval)

    async def get_time_until_reset(self, client_key: str, limit: int) -> int:
        """
        Get accurate time until rate limit reset.
        """
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")

        key = f"rate_limit:{client_key}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.get(key)
            await pipe.ttl(key)
            current_count, ttl = await pipe.execute()
            
            # If key doesn't exist or has no expiry, no waiting needed
            if ttl < 0:
                return 0
                
            current_count = int(current_count) if current_count else 0
            return ttl if current_count >= limit else 0