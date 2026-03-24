"""L2: Supervisor tests — routing logic and report synthesis."""
import pytest


class TestSupervisorRouting:
    def test_resolve_known_prefixes(self):
        from dimensions import resolve_sample_id
        assert resolve_sample_id("CD888888") == "cd"
        assert resolve_sample_id("KS888888") == "aging"
        assert resolve_sample_id("ZL999999") == "zl"
        assert resolve_sample_id("DR888888") == "dr"

    def test_resolve_unknown_prefix(self):
        from dimensions import resolve_sample_id
        assert resolve_sample_id("XX999999") is None
        assert resolve_sample_id("TR888888") is None

    def test_resolve_smy_prefix(self):
        from dimensions import resolve_sample_id
        assert resolve_sample_id("SMY888888") == "smy"
        assert resolve_sample_id("SMX999999") == "smx"

    def test_build_dim_sample_map_from_meta(self):
        """Simulate supervisor logic: meta samples → dim_key targets."""
        from dimensions import resolve_sample_id
        samples = [
            {"sample_id": "CD888888"},
            {"sample_id": "KS888888"},
            {"sample_id": "ZL888888"},
            {"sample_id": "TR888888"},  # Unknown
        ]
        targets, seen = [], set()
        for s in samples:
            sid = s["sample_id"]
            dim = resolve_sample_id(sid)
            if dim and dim not in seen:
                targets.append({"dim_key": dim, "sample_id": sid})
                seen.add(dim)
        assert len(targets) == 3
        dim_keys = {t["dim_key"] for t in targets}
        assert dim_keys == {"cd", "aging", "zl"}


class TestSynthesizeNode:
    def test_empty_results(self):
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

    def test_mixed_results(self):
        from supervisor import synthesize_node
        state = {
            "user_sample_id": "CD888888",
            "user_meta": {"name": "张先生"},
            "dimension_results": [
                {"dimension_key": "cd", "sample_id": "CD888888", "status": "success", "data": "肠道结果"},
                {"dimension_key": "aging", "sample_id": "KS888888", "status": "error", "error": "timeout"},
            ],
        }
        result = synthesize_node(state)
        report = result["synthesized_report"]
        assert "张先生" in report
        assert "CD" in report
        assert "肠道结果" in report
        assert "成功: 1" in report
        assert "AGING" in report

    def test_all_success(self):
        from supervisor import synthesize_node
        state = {
            "user_sample_id": "CD888888",
            "user_meta": {"name": "User"},
            "dimension_results": [
                {"dimension_key": "cd", "sample_id": "CD888888", "status": "success", "data": "A"},
                {"dimension_key": "dr", "sample_id": "DR888888", "status": "success", "data": "B"},
            ],
        }
        result = synthesize_node(state)
        assert "成功: 2" in result["synthesized_report"]

    def test_no_meta_name_fallback(self):
        from supervisor import synthesize_node
        state = {
            "user_sample_id": "CD888888",
            "user_meta": {},
            "dimension_results": [],
        }
        result = synthesize_node(state)
        assert "用户" in result["synthesized_report"]
