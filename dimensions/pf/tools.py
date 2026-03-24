"""皮肤微生物 (PF) dimension tools — v2 API, data_fields.appendixList microbiome structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_pf_data(sample_id: str) -> dict:
    """从API获取皮肤微生物(PF)检测数据。返回有益菌/条件致病菌/有害菌数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        al = df.get("appendixList", {})
        if al:
            return {
                "sample_id": sample_id,
                "status": "success",
                "beneficialData": al.get("beneficialData", []),
                "conditionalPathogenData": al.get("conditionalPathogenData", []),
                "harmfulData": al.get("harmfulData", []),
            }
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
