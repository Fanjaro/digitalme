"""LangGraph StateGraph: supervisor → dimension_worker (Send parallel) → synthesize → END."""
import operator
import threading
from typing import Any, Annotated, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from typing_extensions import TypedDict

from dimensions import get_registry, build_agent
from supervisor import supervisor_node, synthesize_node


class GraphState(TypedDict):
    user_sample_id: str
    user_meta: Optional[dict]
    target_dimensions: list[dict]
    dimension_results: Annotated[list[dict], operator.add]
    synthesized_report: Optional[str]


_agent_cache: dict = {}
_agent_cache_lock = threading.Lock()


def dimension_worker(state: dict) -> dict:
    """Generic worker: route to the correct dimension agent by _dim_key."""
    dim_key = state.get("_dim_key", "")
    sample_id = state.get("_sample_id", "")

    if not dim_key or not sample_id:
        return {
            "dimension_results": [{
                "dimension_key": dim_key,
                "sample_id": sample_id,
                "status": "error",
                "data": "",
                "error": "Missing _dim_key or _sample_id in state",
            }]
        }

    try:
        with _agent_cache_lock:
            if dim_key not in _agent_cache:
                from config import get_llm
                _agent_cache[dim_key] = build_agent(dim_key, get_llm())

        result = _agent_cache[dim_key].invoke({
            "messages": [
                {"role": "user", "content": f"处理样本 {sample_id} 的检测数据，提取关键指标并标准化。"}
            ]
        })
        return {
            "dimension_results": [{
                "dimension_key": dim_key,
                "sample_id": sample_id,
                "status": "success",
                "data": result["messages"][-1].content,
            }]
        }
    except Exception as e:
        return {
            "dimension_results": [{
                "dimension_key": dim_key,
                "sample_id": sample_id,
                "status": "error",
                "data": "",
                "error": str(e),
            }]
        }


def route_to_dimensions(state: dict):
    """Send() fan-out to all target dimensions in parallel."""
    targets = state.get("target_dimensions", [])
    if not targets:
        return [Send("synthesize", state)]
    return [
        Send(
            "dimension_worker",
            {**state, "_dim_key": t["dim_key"], "_sample_id": t["sample_id"]},
        )
        for t in targets
    ]


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("dimension_worker", dimension_worker)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route_to_dimensions)
    g.add_edge("dimension_worker", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()
