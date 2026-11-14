"""LangGraph workflow: load_limits -> validate -> (adjust -> validate)* -> save. Plain Python, no LLM."""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import service
from .rules import MAX_ITERATIONS, apply_fixes, find_violations, num


class State(TypedDict, total=False):
    vehicle_type: str
    input: dict
    current: dict
    limits: dict
    violations: list
    adjustments: list
    iteration: int
    status: str  # pending | valid | adjusted | rejected
    config_id: int


async def load_limits(state: State, config) -> dict:
    deps = config["configurable"]
    rows, _ = await service.get_limit_rows(deps["redis"], deps["session"], state["vehicle_type"])
    limits = {r["field"]: {"min": num(r["min_value"]), "max": num(r["max_value"])} for r in rows}
    return {"limits": limits}


async def validate(state: State) -> dict:
    iteration = state["iteration"] + 1
    violations = find_violations(state["current"], state["limits"])
    if not violations:
        status = "adjusted" if state["adjustments"] else "valid"
    elif iteration >= MAX_ITERATIONS:
        status = "rejected"  # still broken on the last allowed pass
    else:
        status = "pending"
    return {"iteration": iteration, "violations": violations, "status": status}


async def adjust(state: State) -> dict:
    new, log, rejected = apply_fixes(state["current"], state["violations"], state["limits"], state["iteration"])
    update = {"current": new, "adjustments": state["adjustments"] + log}
    if rejected:
        update["status"] = "rejected"
    return update


async def save(state: State, config) -> dict:
    deps = config["configurable"]
    config_id = await service.save_config(
        deps["session"],
        vehicle_type=state["vehicle_type"],
        input=state["input"],
        output=state["current"],
        adjustments=state["adjustments"],
        status=state["status"],
        iterations=state["iteration"],
    )
    return {"config_id": config_id}


def build_graph():
    g = StateGraph(State)
    g.add_node("load_limits", load_limits)
    g.add_node("validate", validate)
    g.add_node("adjust", adjust)
    g.add_node("save", save)

    g.add_edge(START, "load_limits")
    g.add_edge("load_limits", "validate")
    g.add_conditional_edges("validate", lambda s: "adjust" if s["status"] == "pending" else "save",
                            {"adjust": "adjust", "save": "save"})
    g.add_conditional_edges("adjust", lambda s: "save" if s["status"] == "rejected" else "validate",
                            {"save": "save", "validate": "validate"})
    g.add_edge("save", END)
    return g.compile()


graph = build_graph()  # compiled once, reused for every request


async def run_graph(vehicle_type: str, values: dict, redis, session) -> State:
    initial: State = {
        "vehicle_type": vehicle_type,
        "input": {k: num(v) for k, v in values.items()},
        "current": {k: num(v) for k, v in values.items()},
        "adjustments": [],
        "iteration": 0,
        "status": "pending",
    }
    return await graph.ainvoke(initial, config={"configurable": {"redis": redis, "session": session}})
