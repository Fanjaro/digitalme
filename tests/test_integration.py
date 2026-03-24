"""L4: Integration tests — graph compilation, mock data consistency."""
import pytest


class TestGraphCompilation:
    def test_graph_compiles(self):
        from graph import build_graph
        g = build_graph()
        assert g is not None
        assert type(g).__name__ == "CompiledStateGraph"

    def test_graph_state_type(self):
        from graph import GraphState
        fields = GraphState.__annotations__
        for f in ["user_sample_id", "user_meta", "target_dimensions", "dimension_results", "synthesized_report"]:
            assert f in fields


class TestMockDataIntegrity:
    def test_mock_meta_has_9_samples(self):
        from mock_data import MOCK_USER_META
        assert len(MOCK_USER_META["samples"]) == 9

    def test_mock_meta_user_info(self):
        from mock_data import MOCK_USER_META
        assert MOCK_USER_META["name"] == "张明远"
        assert MOCK_USER_META["sex"] == 1

    def test_mock_results_cover_all_9_dims(self):
        from mock_data import MOCK_DIMENSION_RESULTS
        expected = {"aging", "cd", "dr", "my", "sw", "yc", "zl", "gm", "zm"}
        assert set(MOCK_DIMENSION_RESULTS.keys()) == expected

    def test_mock_results_all_success(self):
        from mock_data import MOCK_DIMENSION_RESULTS
        for dim_key, r in MOCK_DIMENSION_RESULTS.items():
            assert r["status"] == "success", f"{dim_key} is not success"
            assert r["data"], f"{dim_key} has empty data"

    def test_dim_sample_map_consistency(self):
        """Mock dim_sample_map aligns with resolve_sample_id."""
        from mock_data import MOCK_USER_META, get_mock_dim_sample_map
        from dimensions import resolve_sample_id
        dim_map = get_mock_dim_sample_map()
        for s in MOCK_USER_META["samples"]:
            sid = s["sample_id"]
            dim = resolve_sample_id(sid)
            if dim:
                assert dim in dim_map


class TestSymptomMapping:
    def test_fatigue_maps_to_aging(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("最近总是感觉很累")
        assert "aging" in dims

    def test_digestion_maps_to_cd(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("消化不好，腹胀")
        assert "cd" in dims

    def test_compound_symptoms(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("很累，消化不好，父亲有糖尿病")
        assert "aging" in dims
        assert "cd" in dims
        assert "dr" in dims

    def test_only_available_dims(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("皮肤不好", available_dims={"cd", "aging"})
        # "pf" not in available_dims, so not returned
        assert "pf" not in dims

    def test_immune_maps_to_my(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("免疫力下降，容易生病")
        assert "my" in dims

    def test_food_maps_to_sw(self):
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("吃牛奶就不舒服")
        assert "sw" in dims

    def test_allergy_maps_to_gm_and_zm(self):
        """'过敏' should map to both gm and zm for storyline consistency."""
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("查一下过敏")
        assert "gm" in dims
        assert "zm" in dims

    def test_tumor_and_allergy_story_line(self):
        """'肿瘤和过敏' should yield zl + gm + zm (round 3 of storyline)."""
        from mock_data import map_symptoms_to_dimensions
        dims = map_symptoms_to_dimensions("帮我也查一下肿瘤和过敏方面")
        assert "zl" in dims
        assert "gm" in dims
        assert "zm" in dims
