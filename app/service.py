import json

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .models import ProportionLimit, VehicleConfig


class VehicleTypeNotFound(Exception):
    pass


def cache_key(vehicle_type: str) -> str:
    return f"limits:{vehicle_type}"


async def get_limit_rows(redis: Redis, session: AsyncSession, vehicle_type: str) -> tuple[list[dict], bool]:
    """Returns (rows, from_cache). Redis first, PostgreSQL on miss."""
    cached = await redis.get(cache_key(vehicle_type))
    if cached:
        return json.loads(cached), True

    result = await session.execute(
        select(ProportionLimit).where(ProportionLimit.vehicle_type == vehicle_type).order_by(ProportionLimit.id)
    )
    rows = [
        {"id": r.id, "vehicle_type": r.vehicle_type, "field": r.field,
         "min_value": r.min_value, "max_value": r.max_value, "unit": r.unit}
        for r in result.scalars()
    ]
    if not rows:
        raise VehicleTypeNotFound(vehicle_type)
    await redis.set(cache_key(vehicle_type), json.dumps(rows), ex=settings.limits_cache_ttl)
    return rows, False


async def save_config(session: AsyncSession, **data) -> int:
    row = VehicleConfig(**data)
    session.add(row)
    await session.commit()
    return row.id
