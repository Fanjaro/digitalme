"""Supervisor node: fetch user meta, resolve dimensions, synthesize results."""
import logging
from dimensions import resolve_sample_id
from skills.extract_meta import MetaExtractor

logger = logging.getLogger(__name__)


def supervisor_node(state: dict) -> dict:
    """Fetch user meta inline and determine target dimensions from sample list."""
    sample_id = state["user_sample_id"]

    extractor = MetaExtractor()
    user_data = extractor.fetch_metadata(sample_id)
    meta = extractor.process_user_data(user_data, sample_id) if user_data else {}

    samples = meta.get("samples", [])
    targets, seen = [], set()
    for s in samples:
        sid = s.get("sample_id", "")
        dim = resolve_sample_id(sid)
        if dim and dim not in seen:
            targets.append({"dim_key": dim, "sample_id": sid})
            seen.add(dim)
        elif not dim and sid:
            logger.warning("Unregistered sample prefix: sample_id=%s", sid)

    return {"user_meta": meta, "target_dimensions": targets}


def synthesize_node(state: dict) -> dict:
    """Collect dimension results and produce a synthesized report."""
    results = state.get("dimension_results", [])
    meta = state.get("user_meta", {})

    user_name = meta.get("name", "用户")
    sample_id = state.get("user_sample_id", "")

    sections = []
    success_count = 0
    for r in results:
        dim_key = r.get("dimension_key", "unknown")
        status = r.get("status", "unknown")
        data = r.get("data", "")
        if status == "success":
            success_count += 1
            sections.append(f"### {dim_key.upper()} 维度\n{data}")
        else:
            sections.append(f"### {dim_key.upper()} 维度\n处理失败: {r.get('error', status)}")

    report = (
        f"# {user_name} 的综合健康检测报告\n\n"
        f"样本ID: {sample_id}\n"
        f"检测维度: {len(results)} 个 (成功: {success_count})\n\n"
        + "\n\n".join(sections)
    )

    return {"synthesized_report": report}
