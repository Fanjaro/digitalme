"""CD (肠道微生物) dimension tools — v2 API, appendix.sections structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_cd_data(sample_id: str) -> dict:
    """从API获取肠道微生物(CD)检测数据。返回 appendix.sections 结构。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "appendix" in data and "sections" in data["appendix"]:
            return {
                "sample_id": sample_id,
                "status": "success",
                "sections": data["appendix"]["sections"],
            }
        if "data_fields" in data:
            return {
                "sample_id": sample_id,
                "status": "success",
                "data_fields": data["data_fields"],
            }
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
