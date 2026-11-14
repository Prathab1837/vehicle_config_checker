from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProportionLimit(Base):
    __tablename__ = "proportion_limits"
    __table_args__ = (UniqueConstraint("vehicle_type", "field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(50), index=True)
    field: Mapped[str] = mapped_column(String(50))
    min_value: Mapped[float] = mapped_column(Float)
    max_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(10))


class VehicleConfig(Base):
    __tablename__ = "vehicle_configs"
    __table_args__ = (Index("ix_vehicle_configs_status_id", "status", "id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String(50))
    input: Mapped[dict] = mapped_column(JSONB)
    output: Mapped[dict] = mapped_column(JSONB)
    adjustments: Mapped[list] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    iterations: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
