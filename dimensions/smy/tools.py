"""男性私密微生物 (SMY) dimension tools — v2 API, data_fields.appendixList bacterial pathogen structure."""
import requests
from langchain_core.tools import tool
from config import API_V2_SAMPLES

_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_smy_data(sample_id: str) -> dict:
    """从API获取男性私密微生物(SMY)检测数据。返回细菌/真菌/寄生虫病原体、机会致病菌和共生菌数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        al = df.get("appendixList", {})
        if al:
            result = {"sample_id": sample_id, "status": "success"}
            for k in ["bacterial_pathogen", "fungal_pathogen", "opportunistic", "parasitic_pathogen", "commensal"]:
                if k in al:
                    result[k] = al[k]
            aro = df.get("appendixListAro", [])
            if aro:
                result["antibiotic_resistance"] = aro
            return result
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
