"""L3: Dimension agent tests — worker function, build_agent, registry."""
import pytest


class TestDimensionWorker:
    def test_missing_keys_returns_error(self):
        from graph import dimension_worker
        result = dimension_worker({})
        dr = result["dimension_results"][0]
        assert dr["status"] == "error"
        assert "Missing" in dr["error"]

    def test_missing_dim_key(self):
        from graph import dimension_worker
        result = dimension_worker({"_dim_key": "", "_sample_id": "CD888888"})
        dr = result["dimension_results"][0]
        assert dr["status"] == "error"

    def test_missing_sample_id(self):
        from graph import dimension_worker
        result = dimension_worker({"_dim_key": "cd", "_sample_id": ""})
        dr = result["dimension_results"][0]
        assert dr["status"] == "error"


class TestRegistry:
    def test_registry_loads_all_12(self):
        from dimensions import get_registry
        reg = get_registry()
        assert len(reg) == 12

    def test_registry_keys(self):
        from dimensions import get_registry
        reg = get_registry()
        expected = {"cd", "pf", "zl", "my", "zm", "aging", "gm", "sw", "dr", "yc", "smx", "smy"}
        assert set(reg.keys()) == expected

    def test_prefix_map_covers_all(self):
        from dimensions import get_prefix_map
        pm = get_prefix_map()
        assert "CD" in pm
        assert "KS" in pm
        assert "TY" in pm
        assert "SMX" in pm
        assert pm["CD"] == "cd"
        assert pm["KS"] == "aging"

    def test_build_agent_unknown_key_raises(self):
        from dimensions import build_agent
        with pytest.raises(KeyError, match="Unknown dimension"):
            build_agent("nonexistent", None)


class TestRouteToAllDimensions:
    def test_route_empty(self):
        from graph import route_to_dimensions
        from langgraph.types import Send
        result = route_to_dimensions({"target_dimensions": []})
        assert len(result) == 1
        assert isinstance(result[0], Send)

    def test_route_multiple(self):
        from graph import route_to_dimensions
        from langgraph.types import Send
        state = {
            "user_sample_id": "CD888888",
            "target_dimensions": [
                {"dim_key": "cd", "sample_id": "CD888888"},
                {"dim_key": "aging", "sample_id": "KS888888"},
                {"dim_key": "dr", "sample_id": "DR888888"},
            ],
        }
        result = route_to_dimensions(state)
        assert len(result) == 3
        assert all(isinstance(r, Send) for r in result)
