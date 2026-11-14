"""Pure validation / fix logic. No I/O, so it is easy to test."""
from typing import Any

FIELDS = ["length", "width", "height", "wheelbase", "payload"]
MAX_ITERATIONS = 3
EPS = 1e-9


def num(x: float) -> int | float:
    """1950.0000000000002 -> 1950 ; 1950.5 -> 1950.5"""
    x = round(float(x), 2)
    return int(x) if x == int(x) else x


def _r1_broken(v: dict) -> bool:
    return v["wheelbase"] > v["length"] - 700 + EPS


def _r2_broken(v: dict) -> bool:
    return v["height"] > v["width"] * 1.3 + EPS


def find_violations(values: dict, limits: dict[str, dict]) -> list[dict[str, Any]]:
    """limits = {field: {"min": x, "max": y}}"""
    out: list[dict[str, Any]] = []
    for f in FIELDS:
        lim = limits.get(f)
        if lim is None:
            continue
        if values[f] < lim["min"]:
            out.append({"rule": "range", "field": f, "bound": "min", "limit": lim["min"]})
        elif values[f] > lim["max"]:
            out.append({"rule": "range", "field": f, "bound": "max", "limit": lim["max"]})
    if _r1_broken(values):
        out.append({"rule": "R1", "field": "wheelbase"})
    if _r2_broken(values):
        out.append({"rule": "R2", "field": "height"})
    return out


def apply_fixes(values: dict, violations: list[dict], limits: dict[str, dict], iteration: int):
    """Fix ONLY the violations from the last validate pass.

    Returns (new_values, adjustment_log, rejected_reason | None).
    """
    v = dict(values)
    log: list[dict] = []

    def record(field: str, rule: str, new: float) -> None:
        log.append({"iteration": iteration, "field": field, "rule": rule,
                    "from": num(v[field]), "to": num(new)})
        v[field] = num(new)

    # 1) range violations -> clamp to nearest limit (always lands inside its own limits)
    for viol in violations:
        if viol["rule"] == "range":
            record(viol["field"], "range", viol["limit"])

    # 2) cross-field rules (only if still broken after clamping)
    cross = {"R1": ("wheelbase", lambda: v["length"] - 700, _r1_broken),
             "R2": ("height", lambda: v["width"] * 1.3, _r2_broken)}
    for viol in violations:
        if viol["rule"] in cross:
            field, target, still_broken = cross[viol["rule"]]
            if not still_broken(v):
                continue
            new = num(target())
            lim = limits.get(field)
            if lim and not (lim["min"] <= new <= lim["max"]):
                return v, log, f"{viol['rule']} fix would put {field}={new} outside its limits"
            record(field, viol["rule"], new)

    return v, log, None
