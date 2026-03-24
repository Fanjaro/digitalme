"""肿瘤ct-DNA (ZL) dimension tools — v2 API, data_fields.ctDna structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_zl_data(sample_id: str) -> dict:
    """从API获取肿瘤ct-DNA(ZL)检测数据。返回ctDNA突变和肿瘤风险数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        if "ctDna" in df:
            return {
                "sample_id": sample_id,
                "status": "success",
                "ctDna": df["ctDna"],
                "mutations": df.get("mutations", []),
                "tumorTypes": df.get("tumorTypes", []),
            }
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
