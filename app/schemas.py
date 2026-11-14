from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfigIn(BaseModel):
    vehicle_type: str = Field(min_length=1)
    length: float = Field(gt=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    wheelbase: float = Field(gt=0)
    payload: float = Field(gt=0)


class ConfigCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_type: str
    input: dict
    output: dict
    adjustments: list
    status: str
    iterations: int


class ConfigOut(ConfigCreated):
    created_at: datetime


class ConfigList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ConfigOut]


class LimitOut(BaseModel):
    id: int
    vehicle_type: str
    field: str
    min_value: float
    max_value: float
    unit: str


class LimitsOut(BaseModel):
    vehicle_type: str
    cached: bool
    limits: list[LimitOut]


class LimitUpdate(BaseModel):
    min_value: float = Field(gt=0)
    max_value: float = Field(gt=0)

    @model_validator(mode="after")
    def check_order(self):
        if self.min_value > self.max_value:
            raise ValueError("min_value must be <= max_value")
        return self
