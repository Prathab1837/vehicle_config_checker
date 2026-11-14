from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ProportionLimit

SEED = [
    ("3w_cargo", "length", 2800, 3600, "mm"),
    ("3w_cargo", "width", 1200, 1500, "mm"),
    ("3w_cargo", "height", 1700, 2100, "mm"),
    ("3w_cargo", "wheelbase", 1900, 2300, "mm"),
    ("3w_cargo", "payload", 300, 700, "kg"),
]


async def seed_limits(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(ProportionLimit))
    if count:
        return
    session.add_all(
        ProportionLimit(vehicle_type=v, field=f, min_value=lo, max_value=hi, unit=u)
        for v, f, lo, hi, u in SEED
    )
    await session.commit()
