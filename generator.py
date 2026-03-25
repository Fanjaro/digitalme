#!/usr/bin/env python3
"""Auto-generate a new dimension agent folder from data/meta files."""
import argparse
import json
import re
import sys
from pathlib import Path
from textwrap import dedent

PROJECT_ROOT = Path(__file__).parent
DIMENSIONS_DIR = PROJECT_ROOT / "dimensions"


# ---------------------------------------------------------------------------
# 1. Analyze data structure
# ---------------------------------------------------------------------------

STRUCTURE_DETECTORS = [
    # (structure_type, detector_fn)
    ("appendix_sections", lambda d: "appendix" in d and "sections" in d.get("appendix", {})),
    ("appendix_table", lambda d: "appendixTable" in d and isinstance(d["appendixTable"], list)),
    ("data_fields_appendixList_microbiome", lambda d: (
        "data_fields" in d
        and "appendixList" in d.get("data_fields", {})
        and "beneficialData" in d.get("data_fields", {}).get("appendixList", {})
    )),
    ("data_fields_appendixList_bacterial", lambda d: (
        "data_fields" in d
        and "appendixList" in d.get("data_fields", {})
        and "bacterial_pathogen" in d.get("data_fields", {}).get("appendixList", {})
    )),
    ("data_fields_ctdna", lambda d: (
        "data_fields" in d and "ctDna" in d.get("data_fields", {})
    )),
    ("data_fields_unscramble", lambda d: (
        "data_fields" in d and "unscramble" in d.get("data_fields", {})
    )),
    ("data_fields_detection", lambda d: (
        "data_fields" in d and "detection" in d.get("data_fields", {})
    )),
    ("v1_aging_ige", lambda d: (
        "data" in d and "aging" in d.get("data", {})
        and d.get("report_type", "") == "ige"
    )),
    ("v1_aging", lambda d: (
        "data" in d and "aging" in d.get("data", {})
        and d.get("report_type", "") not in ("ige", "IgGFood")
    )),
    ("v1_food_intolerance", lambda d: (
        "data" in d and "chronic_immune_intolerance" in d.get("data", {})
    )),
]


def analyze_data_structure(data: dict) -> dict:
    """Detect API version, structure_type, and extraction paths from sample data."""
    source_url = data.get("source_url", "")
    api_version = "v1" if "/api/v1/" in source_url else "v2"

    structure_type = "unknown"
    for st, detector in STRUCTURE_DETECTORS:
        if detector(data):
            structure_type = st
            break

    paths = _get_extraction_paths(structure_type, data)
    return {
        "api_version": api_version,
        "structure_type": structure_type,
        "paths": paths,
        "sample_id": data.get("sample_id", ""),
    }


def _get_extraction_paths(structure_type: str, data: dict) -> list:
    path_map = {
        "appendix_sections": [{"field": "appendix.sections", "description": "附录章节列表"}],
        "appendix_table": [{"field": "appendixTable", "description": "附录表格数据"}],
        "data_fields_appendixList_microbiome": [
            {"field": "data_fields.appendixList.beneficialData", "description": "有益菌数据"},
            {"field": "data_fields.appendixList.conditionalPathogenData", "description": "条件致病菌"},
            {"field": "data_fields.appendixList.harmfulData", "description": "有害菌数据"},
        ],
        "data_fields_appendixList_bacterial": [
            {"field": "data_fields.appendixList.bacterial_pathogen", "description": "细菌病原体"},
            {"field": "data_fields.appendixList.fungal_pathogen", "description": "真菌病原体"},
            {"field": "data_fields.appendixList.opportunistic", "description": "机会致病菌"},
            {"field": "data_fields.appendixList.parasitic_pathogen", "description": "寄生虫病原体"},
        ],
        "data_fields_ctdna": [
            {"field": "data_fields.ctDna", "description": "ctDNA汇总"},
            {"field": "data_fields.mutations", "description": "突变列表"},
            {"field": "data_fields.tumorTypes", "description": "肿瘤类型列表"},
        ],
        "data_fields_unscramble": [
            {"field": "data_fields.unscramble.cancer", "description": "肿瘤风险"},
            {"field": "data_fields.unscramble.cardiovascular", "description": "心血管风险"},
            {"field": "data_fields.unscramble.digestive_system", "description": "消化系统"},
            {"field": "data_fields.unscramble.infection", "description": "感染风险"},
            {"field": "data_fields.unscramble.metabolic", "description": "代谢风险"},
        ],
        "data_fields_detection": [
            {"field": "data_fields.detection.ability", "description": "能力检测"},
        ],
        "v1_aging": [{"field": "data.aging", "description": "衰老机制数据"}],
        "v1_aging_ige": [{"field": "data.aging", "description": "过敏原IgE数据(v1 aging结构)"}],
        "v1_food_intolerance": [{"field": "data.chronic_immune_intolerance", "description": "食物不耐受数据"}],
    }
    return path_map.get(structure_type, [{"field": "unknown", "description": "未识别"}])


# ---------------------------------------------------------------------------
# 2. Generate config.yaml
# ---------------------------------------------------------------------------

def generate_config_yaml(key: str, display_name: str, prefixes: list[str],
                         analysis: dict, meta: dict) -> str:
    api_version = analysis["api_version"]
    extractor = "DetailedDataExtractor" if api_version == "v1" else "DataExtractor"
    structure_type = analysis["structure_type"]
    paths_lines = []
    for p in analysis["paths"]:
        paths_lines.append(f'    - field: "{p["field"]}"')
        paths_lines.append(f'      description: "{p["description"]}"')
    paths_yaml = "\n".join(paths_lines)
    prefixes_yaml = json.dumps(prefixes)
    prefix_pattern = "|".join(re.escape(p) for p in prefixes)
    pattern = f"^({prefix_pattern})\\\\d+"

    testing_principle = meta.get("检测原理描述", "")
    testing_method = meta.get("检测方法描述", "")
    project_desc = meta.get("检测项目描述", "")

    return (
        f'dimension:\n'
        f'  key: "{key}"\n'
        f'  display_name: "{display_name}"\n'
        f'  display_name_en: ""\n'
        f'  description: "{project_desc}"\n'
        f'\n'
        f'sample_id:\n'
        f'  prefixes: {prefixes_yaml}\n'
        f'  pattern: "{pattern}"\n'
        f'\n'
        f'api:\n'
        f'  version: "{api_version}"\n'
        f'  extractor_class: "{extractor}"\n'
        f'\n'
        f'data_extraction:\n'
        f'  paths:\n'
        f'{paths_yaml}\n'
        f'  structure_type: "{structure_type}"\n'
        f'\n'
        f'medical_expertise:\n'
        f'  domain: "{display_name}"\n'
        f'  keywords: []\n'
        f'  testing_principle: "{testing_principle}"\n'
        f'  testing_method: "{testing_method}"\n'
        f'\n'
        f'report_index:\n'
        f'  fields: []\n'
        f'\n'
        f'reference_files:\n'
        f'  meta_file: ""\n'
        f'  data_file: ""\n'
    )


# ---------------------------------------------------------------------------
# 3. Generate tools.py
# ---------------------------------------------------------------------------

_TOOLS_TEMPLATES = {}

_TOOLS_TEMPLATES["appendix_sections"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, appendix.sections structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回 appendix.sections 结构。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "appendix" in data and "sections" in data["appendix"]:
            return {"sample_id": sample_id, "status": "success", "sections": data["appendix"]["sections"]}
        if "data_fields" in data:
            return {"sample_id": sample_id, "status": "success", "data_fields": data["data_fields"]}
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
'''

_TOOLS_TEMPLATES["appendix_table"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, appendixTable structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回 appendixTable 结构。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "appendixTable" in data:
            return {"sample_id": sample_id, "status": "success", "appendixTable": data["appendixTable"]}
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
'''

_TOOLS_TEMPLATES["data_fields_appendixList_microbiome"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, data_fields.appendixList microbiome structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回有益菌/条件致病菌/有害菌数据。"""
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
'''

_TOOLS_TEMPLATES["data_fields_appendixList_bacterial"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, data_fields.appendixList bacterial pathogen structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回细菌/真菌/寄生虫病原体和机会致病菌数据。"""
    try:
        resp = _SESSION.get(f"{API_V2_SAMPLES}{sample_id}", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = data.get("data_fields", {})
        al = df.get("appendixList", {})
        if al:
            result = {"sample_id": sample_id, "status": "success"}
            for k in ["bacterial_pathogen", "fungal_pathogen", "opportunistic", "parasitic_pathogen"]:
                result[k] = al.get(k, [])
            aro = df.get("appendixListAro", [])
            if aro:
                result["antibiotic_resistance"] = aro
            return result
        return {"sample_id": sample_id, "status": "no_data", "keys": list(data.keys())}
    except Exception as e:
        return {"sample_id": sample_id, "status": "error", "error": str(e)}
'''

_TOOLS_TEMPLATES["data_fields_ctdna"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, data_fields.ctDna structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回ctDNA突变和肿瘤风险数据。"""
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
'''

_TOOLS_TEMPLATES["data_fields_unscramble"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, data_fields.unscramble structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回5大疾病风险(肿瘤/心血管/消化/感染/代谢)数据。"""
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
'''

_TOOLS_TEMPLATES["data_fields_detection"] = '''\
"""${display_name} (${key_upper}) dimension tools — v2 API, data_fields.detection structure."""
import requests
from langchain_core.tools import tool

from config import API_V2_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从API获取${display_name}(${key_upper})检测数据。返回体细胞遗传突变检测数据。"""
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
'''

_TOOLS_TEMPLATES["v1_aging"] = '''\
"""${display_name} (${key_upper}) dimension tools — v1 API, data.aging structure."""
import requests
from langchain_core.tools import tool

from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从v1 API获取${display_name}(${key_upper})检测数据。返回衰老机制评分和异常蛋白数据。"""
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
def analyze_${key}_risks(aging_data: dict) -> dict:
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
'''

_TOOLS_TEMPLATES["v1_aging_ige"] = '''\
"""${display_name} (${key_upper}) dimension tools — v1 API, data.aging structure (report_type=ige)."""
import requests
from langchain_core.tools import tool

from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从v1 API获取${display_name}(${key_upper})检测数据。验证report_type为ige，返回过敏原组份IgE反应性。"""
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
def analyze_${key}_allergen_risks(allergen_data: dict) -> dict:
    """分析过敏原IgE数据，按阳性组份比例排序，识别高风险过敏原类别。"""
    if allergen_data.get("status") != "success":
        return allergen_data
    groups = allergen_data.get("allergen_groups", {})
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
'''

_TOOLS_TEMPLATES["v1_food_intolerance"] = '''\
"""${display_name} (${key_upper}) dimension tools — v1 API, data.chronic_immune_intolerance structure."""
import requests
from langchain_core.tools import tool

from config import API_V1_SAMPLES
_SESSION = requests.Session()
_SESSION.mount("http://", requests.adapters.HTTPAdapter(max_retries=3))


@tool
def fetch_${key}_data(sample_id: str) -> dict:
    """从v1 API获取${display_name}(${key_upper})检测数据。返回食物不耐受IgG各类别数据。"""
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
'''


def generate_tools_py(key: str, display_name: str, structure_type: str) -> str:
    template = _TOOLS_TEMPLATES.get(structure_type)
    if not template:
        template = _TOOLS_TEMPLATES["appendix_table"]  # fallback
    return (
        template
        .replace("${key}", key)
        .replace("${key_upper}", key.upper())
        .replace("${display_name}", display_name)
    )


# ---------------------------------------------------------------------------
# 4. Generate prompt.md
# ---------------------------------------------------------------------------

def generate_prompt_md(key: str, display_name: str, meta: dict, structure_type: str) -> str:
    project_desc = meta.get("检测项目描述", display_name)
    principle = meta.get("检测原理描述", "")
    method = meta.get("检测方法描述", "")

    return dedent(f"""\
        # {display_name} ({key.upper()}) 数据处理 Agent

        你是一个专门处理{display_name}检测数据的医学AI助手。

        ## 检测项目
        - 检测项目描述：{project_desc}
        - 检测原理描述：{principle}
        - 检测方法描述：{method}

        ## 医学背景

        （请根据 {display_name} 的具体医学领域补充详细背景知识）

        ## 任务要求

        1. 使用 `fetch_{key}_data` 工具获取样本的检测数据
        2. 分析返回数据中的关键指标
        3. 输出标准化的检测数据摘要

        ## 输出格式

        以结构化 JSON 格式输出，包含 measurement 数组和 report_index：
        - measurement 中每项包含: name, value, range, abnormal, unit, category, clinical_significance
        - report_index 包含该维度的核心汇总指标
    """)


# ---------------------------------------------------------------------------
# 5. Generate __init__.py
# ---------------------------------------------------------------------------

def generate_init_py(key: str, display_name: str, structure_type: str) -> str:
    has_analyze = structure_type in ("v1_aging", "v1_aging_ige")
    tool_name = f"fetch_{key}_data"
    # v1_aging_ige uses allergen-specific analyze tool name
    if structure_type == "v1_aging_ige":
        analyze_name = f"analyze_{key}_allergen_risks"
    else:
        analyze_name = f"analyze_{key}_risks"

    if has_analyze:
        tools_import = f"from .tools import {tool_name}, {analyze_name}"
        tools_list = f"[{tool_name}, {analyze_name}]"
    else:
        tools_import = f"from .tools import {tool_name}"
        tools_list = f"[{tool_name}]"

    return dedent(f'''\
        """{key.upper()} {display_name} dimension agent."""
        import yaml
        from pathlib import Path
        from langgraph.prebuilt import create_react_agent
        {tools_import}

        _DIR = Path(__file__).parent

        with open(_DIR / "config.yaml", "r", encoding="utf-8") as f:
            CONFIG = yaml.safe_load(f)


        def _load_prompt() -> str:
            with open(_DIR / "prompt.md", "r", encoding="utf-8") as f:
                return f.read()


        def build_agent(llm):
            prompt = ChatPromptTemplate.from_messages([
        ("system", _load_prompt()),
        ("placeholder", "{messages}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
        agent = create_tool_calling_agent(llm=llm, tools={tools_list}, prompt=prompt)
    return AgentExecutor(agent=agent, tools={tools_list}, handle_parsing_errors=True))
    ''')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_dimension(key: str, display_name: str, prefixes: list[str],
                       data_file: str = None, meta_file: str = None,
                       force: bool = False) -> Path:
    """Generate a complete dimension agent folder."""
    target = DIMENSIONS_DIR / key
    if target.exists() and not force:
        print(f"Directory {target} already exists. Use --force to overwrite.")
        sys.exit(1)
    target.mkdir(parents=True, exist_ok=True)

    # Load data file for analysis
    analysis = {"api_version": "v2", "structure_type": "appendix_table", "paths": []}
    if data_file:
        data_path = PROJECT_ROOT / data_file
        if data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            analysis = analyze_data_structure(data)
            print(f"Detected: api={analysis['api_version']}, structure={analysis['structure_type']}")
        else:
            print(f"Warning: data file {data_path} not found, using defaults")

    # Load meta file
    meta = {}
    if meta_file:
        meta_path = PROJECT_ROOT / meta_file
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

    # Generate files
    config_content = generate_config_yaml(key, display_name, prefixes, analysis, meta)
    tools_content = generate_tools_py(key, display_name, analysis["structure_type"])
    prompt_content = generate_prompt_md(key, display_name, meta, analysis["structure_type"])
    init_content = generate_init_py(key, display_name, analysis["structure_type"])

    (target / "config.yaml").write_text(config_content, encoding="utf-8")
    (target / "tools.py").write_text(tools_content, encoding="utf-8")
    (target / "prompt.md").write_text(prompt_content, encoding="utf-8")
    (target / "__init__.py").write_text(init_content, encoding="utf-8")

    print(f"Generated dimension agent: {target}/")
    print(f"  config.yaml  — structure_type: {analysis['structure_type']}")
    print(f"  tools.py     — fetch_{key}_data")
    print(f"  prompt.md    — base prompt (review and enhance)")
    print(f"  __init__.py  — build_agent()")
    return target


def main():
    parser = argparse.ArgumentParser(description="Generate a new dimension agent folder")
    parser.add_argument("--key", required=True, help="Dimension key (folder name)")
    parser.add_argument("--display-name", required=True, help="Chinese display name")
    parser.add_argument("--prefixes", required=True, help="Comma-separated sample ID prefixes")
    parser.add_argument("--data-file", help="Path to _data.json (relative to project root)")
    parser.add_argument("--meta-file", help="Path to _META.json (relative to project root)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing folder")
    args = parser.parse_args()

    prefixes = [p.strip() for p in args.prefixes.split(",")]
    generate_dimension(args.key, args.display_name, prefixes,
                       args.data_file, args.meta_file, args.force)


if __name__ == "__main__":
    main()
