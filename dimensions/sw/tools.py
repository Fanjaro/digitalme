"""食物不耐受IgG (SW) dimension tools — v1 API, data.chronic_immune_intolerance structure."""
import requests
from langchain_core.tools import tool
from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_sw_data(sample_id: str) -> dict:
    """从v1 API获取食物不耐受IgG(SW)检测数据。返回食物不耐受IgG各类别数据。"""
    try:
        resp = _SESSION.get(f"{API_V1_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cii = data.get("data", {}).get("chronic_immune_intolerance", {})
        if not cii:
            return {"sample_id": sample_id, "status": "no_data"}
        categories = {}
        for cat_name, cat_data in cii.items():
            if not isinstance(cat_data, dict):
                continue
            vals = cat_data.get("value", [])
            lows = cat_data.get("lower", [])
            highs = cat_data.get("upper", [])
            abnormal = sum(
                1 for v, lo, hi in zip(vals, lows, highs)
                if isinstance(v, (int, float)) and isinstance(lo, (int, float)) and isinstance(hi, (int, float))
                and (v < lo or v > hi)
            )
            categories[cat_name] = {
                "total_items": len(cat_data.get("uniprot", [])),
                "abnormal_items": abnormal,
                "pred_quantile": cat_data.get("pred_quantile"),
                "pred_raw": cat_data.get("pred_raw"),
            }
        return {
            "sample_id": sample_id,
            "status": "success",
            "report_type": data.get("report_type", ""),
            "food_categories": categories,
        }
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
