import json
from typing import Any, Optional
import redis
from functools import wraps
from .config import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def cache_key(prefix: str, *args, **kwargs) -> str:
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)

def cache(expire: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = cache_key(func.__name__, *args, **kwargs)
            
            cached_value = redis_client.get(key)
            if cached_value:
                return json.loads(cached_value)
            
            result = await func(*args, **kwargs)
            
            redis_client.setex(
                key,
                expire,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix: str, *args, **kwargs):
    pattern = cache_key(prefix, *args, **kwargs)
    keys = redis_client.keys(f"{pattern}*")
    if keys:
        redis_client.delete(*keys)

class CacheManager:
    @staticmethod
    async def get_survey(survey_id: int) -> Optional[dict]:
        """Get survey from cache."""
        key = cache_key("survey", survey_id)
        data = redis_client.get(key)
        return json.loads(data) if data else None

    @staticmethod
    async def set_survey(survey_id: int, data: dict, expire: int = 300):
        """Cache survey data."""
        key = cache_key("survey", survey_id)
        redis_client.setex(key, expire, json.dumps(data))

    @staticmethod
    async def invalidate_survey(survey_id: int):
        """Invalidate survey cache."""
        invalidate_cache("survey", survey_id)

    @staticmethod
    async def get_survey_results(survey_id: int) -> Optional[dict]:
        """Get survey results from cache."""
        key = cache_key("survey_results", survey_id)
        data = redis_client.get(key)
        return json.loads(data) if data else None

    @staticmethod
    async def set_survey_results(survey_id: int, data: dict, expire: int = 300):
        """Cache survey results."""
        key = cache_key("survey_results", survey_id)
        redis_client.setex(key, expire, json.dumps(data))

    @staticmethod
    async def invalidate_survey_results(survey_id: int):
        """Invalidate survey results cache."""
        invalidate_cache("survey_results", survey_id) 