from contextlib import asynccontextmanager
from typing import Literal

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import service
from .config import settings
from .db import SessionLocal, engine, get_session
from .graph import run_graph
from .models import Base, ProportionLimit, VehicleConfig
from .schemas import ConfigCreated, ConfigIn, ConfigList, ConfigOut, LimitsOut, LimitUpdate
from .seed import seed_limits


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        await seed_limits(s)
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()
    await engine.dispose()


app = FastAPI(title="Vehicle Config Checker", lifespan=lifespan)


def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis


@app.post("/configs", response_model=ConfigCreated)
async def create_config(body: ConfigIn, session: AsyncSession = Depends(get_session),
                        redis: aioredis.Redis = Depends(get_redis)):
    values = body.model_dump(exclude={"vehicle_type"})
    try:
        state = await run_graph(body.vehicle_type, values, redis, session)
    except service.VehicleTypeNotFound:
        raise HTTPException(404, f"Unknown vehicle type: {body.vehicle_type}")
    return await session.get(VehicleConfig, state["config_id"])


@app.get("/configs/{config_id}", response_model=ConfigOut)
async def get_config(config_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(VehicleConfig, config_id)
    if not row:
        raise HTTPException(404, "Config not found")
    return row


@app.get("/configs", response_model=ConfigList)
async def list_configs(status: Literal["valid", "adjusted", "rejected"] | None = None,
                       limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                       session: AsyncSession = Depends(get_session)):
    q = select(VehicleConfig)
    count_q = select(func.count()).select_from(VehicleConfig)
    if status:
        q, count_q = q.where(VehicleConfig.status == status), count_q.where(VehicleConfig.status == status)
    total = await session.scalar(count_q)
    rows = (await session.scalars(q.order_by(VehicleConfig.id.desc()).limit(limit).offset(offset))).all()
    return ConfigList(total=total, limit=limit, offset=offset, items=rows)


@app.get("/limits/{vehicle_type}", response_model=LimitsOut)
async def get_limits(vehicle_type: str, session: AsyncSession = Depends(get_session),
                     redis: aioredis.Redis = Depends(get_redis)):
    try:
        rows, cached = await service.get_limit_rows(redis, session, vehicle_type)
    except service.VehicleTypeNotFound:
        raise HTTPException(404, f"Unknown vehicle type: {vehicle_type}")
    return {"vehicle_type": vehicle_type, "cached": cached, "limits": rows}


@app.put("/limits/{vehicle_type}/{field}")
async def update_limit(vehicle_type: str, field: str, body: LimitUpdate,
                       session: AsyncSession = Depends(get_session),
                       redis: aioredis.Redis = Depends(get_redis)):
    row = (await session.scalars(select(ProportionLimit).where(
        ProportionLimit.vehicle_type == vehicle_type, ProportionLimit.field == field))).first()
    if not row:
        raise HTTPException(404, "Limit not found for this vehicle type / field")
    row.min_value, row.max_value = body.min_value, body.max_value
    await session.commit()
    await redis.delete(service.cache_key(vehicle_type))
    return {"vehicle_type": vehicle_type, "field": field,
            "min_value": row.min_value, "max_value": row.max_value, "unit": row.unit}
