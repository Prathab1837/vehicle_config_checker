import pytest

from app import graph as graph_mod
from app import service

ROWS = [
    {"field": "length", "min_value": 2800, "max_value": 3600},
    {"field": "width", "min_value": 1200, "max_value": 1500},
    {"field": "height", "min_value": 1700, "max_value": 2100},
    {"field": "wheelbase", "min_value": 1900, "max_value": 2300},
    {"field": "payload", "min_value": 300, "max_value": 700},
]


@pytest.fixture(autouse=True)
def fake_io(monkeypatch):
    async def fake_limits(redis, session, vt):
        if vt != "3w_cargo":
            raise service.VehicleTypeNotFound(vt)
        return ROWS, False

    async def fake_save(session, **data):
        return 1

    monkeypatch.setattr(service, "get_limit_rows", fake_limits)
    monkeypatch.setattr(service, "save_config", fake_save)


async def run(**v):
    base = dict(length=3000, width=1400, height=1800, wheelbase=2200, payload=500)
    base.update(v)
    return await graph_mod.run_graph("3w_cargo", base, None, None)


async def test_worked_example():
    s = await run(width=1600, height=2050)
    assert s["status"] == "adjusted"
    assert s["iteration"] == 3
    assert s["current"] == {"length": 3000, "width": 1500, "height": 1950, "wheelbase": 2200, "payload": 500}
    assert s["adjustments"] == [
        {"iteration": 1, "field": "width", "rule": "range", "from": 1600, "to": 1500},
        {"iteration": 2, "field": "height", "rule": "R2", "from": 2050, "to": 1950},
    ]


async def test_valid_needs_no_fixes():
    s = await run()
    assert s["status"] == "valid" and s["adjustments"] == [] and s["iteration"] == 1


async def test_r1_fix():
    s = await run(length=2900, wheelbase=2300)  # 2300 > 2900-700 -> wheelbase 2200
    assert s["status"] == "adjusted"
    assert s["current"]["wheelbase"] == 2200
    assert s["adjustments"][0]["rule"] == "R1"


async def test_rejected_when_r1_fix_leaves_wheelbase_limits():
    s = await run(length=2500, wheelbase=2000)  # length -> 2800, then R1 ok; so adjusted
    assert s["status"] == "adjusted"
    s = await run(length=2800, wheelbase=2250, payload=500)  # R1 -> 2100, inside 1900..2300
    assert s["current"]["wheelbase"] == 2100


async def test_rejected_when_r2_fix_leaves_height_limits():
    s = await run(width=1200, height=2000)  # R2 -> 1560 < min 1700
    assert s["status"] == "rejected"


async def test_unknown_vehicle_type():
    with pytest.raises(service.VehicleTypeNotFound):
        await graph_mod.run_graph("5w_unknown", dict(length=1, width=1, height=1, wheelbase=1, payload=1), None, None)
