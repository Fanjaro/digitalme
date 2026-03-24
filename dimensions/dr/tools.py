"""5大疾病风险 (DR) dimension tools — v2 API, data_fields.unscramble structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_dr_data(sample_id: str) -> dict:
    """从API获取5大疾病风险(DR)检测数据。返回5大疾病风险(肿瘤/心血管/消化/感染/代谢)数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        unscramble = df.get("unscramble", {})
        if unscramble:
            return {
                "sample_id": sample_id,
                "status": "success",
                "cancer": unscramble.get("cancer", []),
                "cardiovascular": unscramble.get("cardiovascular", []),
                "digestive_system": unscramble.get("digestive_system", []),
                "infection": unscramble.get("infection", []),
                "metabolic": unscramble.get("metabolic", []),
            }
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
