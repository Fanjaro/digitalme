"""过敏原IgE (GM) dimension tools — v1 API, data.aging structure (report_type=ige)."""
import requests
from langchain_core.tools import tool
from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_gm_data(sample_id: str) -> dict:
    """从v1 API获取过敏原IgE(GM)检测数据。验证report_type为ige，返回各过敏原组份的IgE反应性评分。"""
    try:
        resp = _SESSION.get(f"{API_V1_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()

        report_type = data.get("report_type", "")
        if report_type != "ige":
            return {"sample_id": sample_id, "status": "wrong_report_type",
                    "expected": "ige", "got": report_type}

        if "data" not in data or "aging" not in data.get("data", {}):
            return {"sample_id": sample_id, "status": "no_data"}

        aging = data["data"]["aging"]
        allergen_groups = {}
        for group_name, group_data in aging.items():
            if not isinstance(group_data, dict):
                continue
            vals = group_data.get("value", [])
            lows = group_data.get("lower", [])
            highs = group_data.get("upper", [])
            uniprots = group_data.get("uniprot", [])
            # 统计阳性（高于上限）的过敏原组份
            positive_count = sum(
                1 for v, lo, hi in zip(vals, lows, highs)
                if isinstance(v, (int, float)) and isinstance(hi, (int, float))
                and v > hi
            )
            allergen_groups[group_name] = {
                "pred_quantile": group_data.get("pred_quantile"),
                "pred_raw": group_data.get("pred_raw"),
                "total_components": len(uniprots),
                "positive_components": positive_count,
            }
        return {
            "sample_id": sample_id,
            "status": "success",
            "report_type": report_type,
            "allergen_groups": allergen_groups,
        }
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}


@tool
def analyze_gm_allergen_risks(allergen_data: dict) -> dict:
    """分析过敏原IgE数据，按阳性组份比例排序，识别高风险过敏原类别。"""
    if allergen_data.get("status") != "success":
        return allergen_data
    groups = allergen_data.get("allergen_groups", {})
    # 按阳性比例排序
    ranked = sorted(
        groups.items(),
        key=lambda x: (x[1]["positive_components"] / max(x[1]["total_components"], 1)),
        reverse=True,
    )
    total_components = sum(v["total_components"] for _, v in ranked)
    total_positive = sum(v["positive_components"] for _, v in ranked)
    return {
        "sample_id": allergen_data["sample_id"],
        "top_allergen_groups": [{"name": k, **v} for k, v in ranked[:5]],
        "total_groups": len(ranked),
        "total_components": total_components,
        "total_positive": total_positive,
        "overall_positive_rate": f"{total_positive / max(total_components, 1) * 100:.1f}%",
    }
