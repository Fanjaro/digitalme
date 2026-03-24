"""衰老/亚健康 (AGING) dimension tools — v1 API, data.aging structure."""
import requests
from langchain_core.tools import tool
from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_aging_data(sample_id: str) -> dict:
    """从v1 API获取衰老/亚健康(AGING)检测数据。返回衰老机制评分和异常蛋白数据。"""
    try:
        resp = _SESSION.get(f"{API_V1_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data or "aging" not in data.get("data", {}):
            return {"sample_id": sample_id, "status": "no_aging_data"}
        aging = data["data"]["aging"]
        mechanisms = {}
        for mech_name, mech_data in aging.items():
            if not isinstance(mech_data, dict):
                continue
            vals = mech_data.get("value", [])
            lows = mech_data.get("lower", [])
            highs = mech_data.get("upper", [])
            abnormal = sum(
                1 for v, lo, hi in zip(vals, lows, highs)
                if isinstance(v, (int, float)) and isinstance(lo, (int, float)) and isinstance(hi, (int, float))
                and (v < lo or v > hi)
            )
            mechanisms[mech_name] = {
                "pred_quantile": mech_data.get("pred_quantile"),
                "pred_raw": mech_data.get("pred_raw"),
                "total_proteins": len(mech_data.get("uniprot", [])),
                "abnormal_proteins": abnormal,
            }
        return {
            "sample_id": sample_id,
            "status": "success",
            "report_type": data.get("report_type", ""),
            "mechanisms": mechanisms,
        }
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}


@tool
def analyze_aging_risks(aging_data: dict) -> dict:
    """分析衰老数据中的风险蛋白和高危机制，按 pred_quantile 排序。"""
    if aging_data.get("status") != "success":
        return aging_data
    mechs = aging_data.get("mechanisms", {})
    ranked = sorted(mechs.items(), key=lambda x: x[1].get("pred_quantile") or 0, reverse=True)
    return {
        "sample_id": aging_data["sample_id"],
        "top_risks": [{"name": k, **v} for k, v in ranked[:5]],
        "total_mechanisms": len(ranked),
        "total_proteins": sum(v["total_proteins"] for _, v in ranked),
    }
