"""体细胞遗传突变 (YC) dimension tools — v2 API, data_fields.detection structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_yc_data(sample_id: str) -> dict:
    """从API获取体细胞遗传突变(YC)检测数据。返回体细胞遗传突变检测数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        detection = df.get("detection", {})
        if detection:
            return {
                "sample_id": sample_id,
                "status": "success",
                "ability": detection.get("ability", []),
                "diseases": detection.get("diseases", []),
                "drug_metabolic_capacity": detection.get("drug_metabolic_capacity", []),
                "features": detection.get("features", []),
                "identity": detection.get("identity", []),
                "sensitivity": detection.get("sensitivity", []),
            }
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
