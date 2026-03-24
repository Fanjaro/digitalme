"""L1: Tool-level tests — mock HTTP to test actual tool functions for all 12 dimensions.

Each dimension gets 3 tests: happy path, no_data, error.
Uses `responses` library to intercept HTTP calls.
"""
import json
import pytest
import responses
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "skills" / "data"

# Import API base URLs
from config import API_V1_SAMPLES, API_V2_SAMPLES


def _load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


# ---- Helper: build mock URL ----

def _v2_url(sample_id: str) -> str:
    return f"{API_V2_SAMPLES}{sample_id}"


def _v1_url(sample_id: str) -> str:
    return f"{API_V1_SAMPLES}{sample_id}"


# ===========================================================================
# CD: fetch_cd_data (v2, appendix.sections)
# ===========================================================================

class TestCDTool:
    @responses.activate
    def test_happy(self):
        from dimensions.cd.tools import fetch_cd_data
        data = _load_json("肠道微生物_data.json")
        responses.add(responses.GET, _v2_url("CD888888"), json=data, status=200)
        result = fetch_cd_data.invoke({"sample_id": "CD888888"})
        assert result["status"] == "success"
        assert result["sample_id"] == "CD888888"

    @responses.activate
    def test_no_data(self):
        from dimensions.cd.tools import fetch_cd_data
        responses.add(responses.GET, _v2_url("CD000000"), json={"other": "stuff"}, status=200)
        result = fetch_cd_data.invoke({"sample_id": "CD000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.cd.tools import fetch_cd_data
        responses.add(responses.GET, _v2_url("CD999999"), status=500)
        result = fetch_cd_data.invoke({"sample_id": "CD999999"})
        assert result["status"] == "error"
        assert "error" in result


# ===========================================================================
# PF: fetch_pf_data (v2, data_fields.appendixList microbiome)
# ===========================================================================

class TestPFTool:
    @responses.activate
    def test_happy(self):
        from dimensions.pf.tools import fetch_pf_data
        data = _load_json("皮肤微生物数据_data.json")
        responses.add(responses.GET, _v2_url("PF888888"), json=data, status=200)
        result = fetch_pf_data.invoke({"sample_id": "PF888888"})
        assert result["status"] == "success"
        assert "beneficialData" in result or "data_fields" in str(result)

    @responses.activate
    def test_no_data(self):
        from dimensions.pf.tools import fetch_pf_data
        responses.add(responses.GET, _v2_url("PF000000"), json={"other": "stuff"}, status=200)
        result = fetch_pf_data.invoke({"sample_id": "PF000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.pf.tools import fetch_pf_data
        responses.add(responses.GET, _v2_url("PF999999"), status=500)
        result = fetch_pf_data.invoke({"sample_id": "PF999999"})
        assert result["status"] == "error"


# ===========================================================================
# ZL: fetch_zl_data (v2, data_fields.ctDna)
# ===========================================================================

class TestZLTool:
    @responses.activate
    def test_happy(self):
        from dimensions.zl.tools import fetch_zl_data
        data = _load_json("肿瘤ct-DNA_data.json")
        responses.add(responses.GET, _v2_url("ZL888888"), json=data, status=200)
        result = fetch_zl_data.invoke({"sample_id": "ZL888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.zl.tools import fetch_zl_data
        responses.add(responses.GET, _v2_url("ZL000000"), json={"other": "stuff"}, status=200)
        result = fetch_zl_data.invoke({"sample_id": "ZL000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.zl.tools import fetch_zl_data
        responses.add(responses.GET, _v2_url("ZL999999"), status=500)
        result = fetch_zl_data.invoke({"sample_id": "ZL999999"})
        assert result["status"] == "error"


# ===========================================================================
# MY: fetch_my_data (v2, appendixTable)
# ===========================================================================

class TestMYTool:
    @responses.activate
    def test_happy(self):
        from dimensions.my.tools import fetch_my_data
        data = _load_json("抗体免疫力_data.json")
        responses.add(responses.GET, _v2_url("MY888888"), json=data, status=200)
        result = fetch_my_data.invoke({"sample_id": "MY888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.my.tools import fetch_my_data
        responses.add(responses.GET, _v2_url("MY000000"), json={"other": "stuff"}, status=200)
        result = fetch_my_data.invoke({"sample_id": "MY000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.my.tools import fetch_my_data
        responses.add(responses.GET, _v2_url("MY999999"), status=500)
        result = fetch_my_data.invoke({"sample_id": "MY999999"})
        assert result["status"] == "error"


# ===========================================================================
# ZM: fetch_zm_data (v2, appendixTable)
# ===========================================================================

class TestZMTool:
    @responses.activate
    def test_happy(self):
        from dimensions.zm.tools import fetch_zm_data
        data = _load_json("自身免疫抗体_data.json")
        responses.add(responses.GET, _v2_url("ZM888888"), json=data, status=200)
        result = fetch_zm_data.invoke({"sample_id": "ZM888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.zm.tools import fetch_zm_data
        responses.add(responses.GET, _v2_url("ZM000000"), json={"other": "stuff"}, status=200)
        result = fetch_zm_data.invoke({"sample_id": "ZM000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.zm.tools import fetch_zm_data
        responses.add(responses.GET, _v2_url("ZM999999"), status=500)
        result = fetch_zm_data.invoke({"sample_id": "ZM999999"})
        assert result["status"] == "error"


# ===========================================================================
# AGING: fetch_aging_data (v1)
# ===========================================================================

class TestAgingTool:
    @responses.activate
    def test_happy(self):
        from dimensions.aging.tools import fetch_aging_data
        data = _load_json("衰老数据_data.json")
        responses.add(responses.GET, _v1_url("KS888888"), json=data, status=200)
        result = fetch_aging_data.invoke({"sample_id": "KS888888"})
        assert result["status"] == "success"
        assert "mechanisms" in result

    @responses.activate
    def test_no_data(self):
        from dimensions.aging.tools import fetch_aging_data
        responses.add(responses.GET, _v1_url("KS000000"), json={"other": "stuff"}, status=200)
        result = fetch_aging_data.invoke({"sample_id": "KS000000"})
        assert result["status"] in ("no_data", "no_aging_data")

    @responses.activate
    def test_error(self):
        from dimensions.aging.tools import fetch_aging_data
        responses.add(responses.GET, _v1_url("KS999999"), status=500)
        result = fetch_aging_data.invoke({"sample_id": "KS999999"})
        assert result["status"] == "error"


# ===========================================================================
# GM: fetch_gm_data (v1, ige)
# ===========================================================================

class TestGMTool:
    @responses.activate
    def test_happy(self):
        from dimensions.gm.tools import fetch_gm_data
        data = _load_json("过敏原组份IgE检测_data.json")
        responses.add(responses.GET, _v1_url("GM888888"), json=data, status=200)
        result = fetch_gm_data.invoke({"sample_id": "GM888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.gm.tools import fetch_gm_data
        responses.add(responses.GET, _v1_url("GM000000"), json={"other": "stuff"}, status=200)
        result = fetch_gm_data.invoke({"sample_id": "GM000000"})
        assert result["status"] in ("no_data", "wrong_report_type")

    @responses.activate
    def test_error(self):
        from dimensions.gm.tools import fetch_gm_data
        responses.add(responses.GET, _v1_url("GM999999"), status=500)
        result = fetch_gm_data.invoke({"sample_id": "GM999999"})
        assert result["status"] == "error"


# ===========================================================================
# SW: fetch_sw_data (v1, IgGFood)
# ===========================================================================

class TestSWTool:
    @responses.activate
    def test_happy(self):
        from dimensions.sw.tools import fetch_sw_data
        data = _load_json("食物不耐受IgG检测_data.json")
        responses.add(responses.GET, _v1_url("SW888888"), json=data, status=200)
        result = fetch_sw_data.invoke({"sample_id": "SW888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.sw.tools import fetch_sw_data
        responses.add(responses.GET, _v1_url("SW000000"), json={"other": "stuff"}, status=200)
        result = fetch_sw_data.invoke({"sample_id": "SW000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.sw.tools import fetch_sw_data
        responses.add(responses.GET, _v1_url("SW999999"), status=500)
        result = fetch_sw_data.invoke({"sample_id": "SW999999"})
        assert result["status"] == "error"


# ===========================================================================
# DR: fetch_dr_data (v2, data_fields.unscramble)
# ===========================================================================

class TestDRTool:
    @responses.activate
    def test_happy(self):
        from dimensions.dr.tools import fetch_dr_data
        data = _load_json("5大疾病数据_data.json")
        responses.add(responses.GET, _v2_url("DR888888"), json=data, status=200)
        result = fetch_dr_data.invoke({"sample_id": "DR888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.dr.tools import fetch_dr_data
        responses.add(responses.GET, _v2_url("DR000000"), json={"other": "stuff"}, status=200)
        result = fetch_dr_data.invoke({"sample_id": "DR000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.dr.tools import fetch_dr_data
        responses.add(responses.GET, _v2_url("DR999999"), status=500)
        result = fetch_dr_data.invoke({"sample_id": "DR999999"})
        assert result["status"] == "error"


# ===========================================================================
# YC: fetch_yc_data (v2, data_fields.detection)
# ===========================================================================

class TestYCTool:
    @responses.activate
    def test_happy(self):
        from dimensions.yc.tools import fetch_yc_data
        data = _load_json("体细胞遗传突变_data.json")
        responses.add(responses.GET, _v2_url("YC888888"), json=data, status=200)
        result = fetch_yc_data.invoke({"sample_id": "YC888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.yc.tools import fetch_yc_data
        responses.add(responses.GET, _v2_url("YC000000"), json={"other": "stuff"}, status=200)
        result = fetch_yc_data.invoke({"sample_id": "YC000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.yc.tools import fetch_yc_data
        responses.add(responses.GET, _v2_url("YC999999"), status=500)
        result = fetch_yc_data.invoke({"sample_id": "YC999999"})
        assert result["status"] == "error"


# ===========================================================================
# SMX: fetch_smx_data (v2, data_fields.appendixList bacterial)
# ===========================================================================

class TestSMXTool:
    @responses.activate
    def test_happy(self):
        from dimensions.smx.tools import fetch_smx_data
        data = _load_json("女性私密微生物_data.json")
        responses.add(responses.GET, _v2_url("SMX888888"), json=data, status=200)
        result = fetch_smx_data.invoke({"sample_id": "SMX888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.smx.tools import fetch_smx_data
        responses.add(responses.GET, _v2_url("SMX000000"), json={"other": "stuff"}, status=200)
        result = fetch_smx_data.invoke({"sample_id": "SMX000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.smx.tools import fetch_smx_data
        responses.add(responses.GET, _v2_url("SMX999999"), status=500)
        result = fetch_smx_data.invoke({"sample_id": "SMX999999"})
        assert result["status"] == "error"


# ===========================================================================
# SMY: fetch_smy_data (v2, data_fields.appendixList bacterial + commensal)
# ===========================================================================

class TestSMYTool:
    @responses.activate
    def test_happy(self):
        from dimensions.smy.tools import fetch_smy_data
        data = _load_json("男性私密微生物_data.json")
        responses.add(responses.GET, _v2_url("SMY888888"), json=data, status=200)
        result = fetch_smy_data.invoke({"sample_id": "SMY888888"})
        assert result["status"] == "success"

    @responses.activate
    def test_no_data(self):
        from dimensions.smy.tools import fetch_smy_data
        responses.add(responses.GET, _v2_url("SMY000000"), json={"other": "stuff"}, status=200)
        result = fetch_smy_data.invoke({"sample_id": "SMY000000"})
        assert result["status"] == "no_data"

    @responses.activate
    def test_error(self):
        from dimensions.smy.tools import fetch_smy_data
        responses.add(responses.GET, _v2_url("SMY999999"), status=500)
        result = fetch_smy_data.invoke({"sample_id": "SMY999999"})
        assert result["status"] == "error"
