"""抗体免疫力 (MY) dimension tools — v2 API, appendixTable structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_my_data(sample_id: str) -> dict:
    """从API获取抗体免疫力(MY)检测数据。返回 appendixTable 结构。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "appendixTable" in data:
            return {"sample_id": sample_id, "status": "success", "appendixTable": data["appendixTable"]}
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
