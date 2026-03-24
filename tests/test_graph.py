"""Phase 7 - Test 43/44: Graph compilation and supervisor logic tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_graph_compiles():
    from graph import build_graph
    g = build_graph()
    assert g is not None
    assert type(g).__name__ == "CompiledStateGraph"


def test_graph_state_type():
    from graph import GraphState
    fields = GraphState.__annotations__
    assert "user_sample_id" in fields
    assert "user_meta" in fields
    assert "target_dimensions" in fields
    assert "dimension_results" in fields
    assert "synthesized_report" in fields


def test_synthesize_node_empty():
    from supervisor import synthesize_node
    state = {
        "user_sample_id": "CD888888",
        "user_meta": {"name": "Test"},
        "dimension_results": [],
    }
    result = synthesize_node(state)
    assert "synthesized_report" in result
    assert "Test" in result["synthesized_report"]
    assert "成功: 0" in result["synthesized_report"]


def test_synthesize_node_with_results():
    from supervisor import synthesize_node
    state = {
        "user_sample_id": "CD888888",
        "user_meta": {"name": "Demo"},
        "dimension_results": [
            {"dimension_key": "cd", "sample_id": "CD888888", "status": "success", "data": "肠道检测结果"},
            {"dimension_key": "zl", "sample_id": "ZL888888", "status": "error", "error": "timeout"},
        ],
    }
    result = synthesize_node(state)
    report = result["synthesized_report"]
    assert "Demo" in report
    assert "CD" in report
    assert "肠道检测结果" in report
    assert "ZL" in report
    assert "成功: 1" in report


def test_route_to_dimensions_empty():
    from graph import route_to_dimensions
    from langgraph.types import Send
    state = {"target_dimensions": []}
    result = route_to_dimensions(state)
    assert len(result) == 1
    assert isinstance(result[0], Send)


def test_route_to_dimensions_multiple():
    from graph import route_to_dimensions
    from langgraph.types import Send
    state = {
        "user_sample_id": "CD888888",
        "target_dimensions": [
            {"dim_key": "cd", "sample_id": "CD888888"},
            {"dim_key": "zl", "sample_id": "ZL888888"},
        ],
    }
    result = route_to_dimensions(state)
    assert len(result) == 2
    assert all(isinstance(r, Send) for r in result)


def test_dimension_worker_missing_keys():
    from graph import dimension_worker
    result = dimension_worker({})
    assert result["dimension_results"][0]["status"] == "error"
    assert "Missing" in result["dimension_results"][0]["error"]


def test_resolve_integration_with_supervisor():
    """Test that resolve_sample_id correctly handles samples from meta."""
    from dimensions import resolve_sample_id
    # Simulate samples from meta
    test_samples = [
        {"sample_id": "CD888888"},
        {"sample_id": "PF888888"},
        {"sample_id": "ZL999999"},
        {"sample_id": "KS901068"},
        {"sample_id": "TR888888"},  # Unknown prefix
        {"sample_id": "EM888888"},  # Unknown prefix
    ]
    targets, seen = [], set()
    for s in test_samples:
        sid = s["sample_id"]
        dim = resolve_sample_id(sid)
        if dim and dim not in seen:
            targets.append({"dim_key": dim, "sample_id": sid})
            seen.add(dim)

    assert len(targets) == 4  # cd, pf, zl, aging
    dim_keys = [t["dim_key"] for t in targets]
    assert "cd" in dim_keys
    assert "pf" in dim_keys
    assert "zl" in dim_keys
    assert "aging" in dim_keys


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
