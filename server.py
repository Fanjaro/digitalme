#!/usr/bin/env python3
"""FastAPI + WebSocket server for DigitalMe guided health chat."""
import argparse
import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class ChatState(str, Enum):
    GREETING = "greeting"
    WAIT_DESCRIPTION = "wait_description"
    HEALTH_INTERVIEW = "health_interview"
    WAIT_INTERVIEW_ANSWER = "wait_interview_answer"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    SUGGEST_DIMS = "suggest_dims"
    WAIT_CONFIRM = "wait_confirm"
    RUNNING = "running"
    ROUND_RESULT = "round_result"
    FINAL_REPORT = "final_report"
    DONE = "done"


@dataclass
class SessionState:
    user_id: str = ""
    user_meta: dict = field(default_factory=dict)
    dim_sample_map: dict = field(default_factory=dict)  # dim_key -> sample_id
    state: ChatState = ChatState.GREETING
    analyzed_dims: list[str] = field(default_factory=list)
    pending_dims: list[str] = field(default_factory=list)
    round_number: int = 0
    all_results: dict = field(default_factory=dict)  # dim_key -> result
    symptom_text: str = ""
    interview_answers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

_mock_mode = True  # set via CLI arg or env

app = FastAPI(title="DigitalMe Health Chat")
_STATIC = Path(__file__).parent / "static"


def set_mock_mode(enabled: bool):
    global _mock_mode
    _mock_mode = enabled


@app.get("/")
async def index():
    return FileResponse(_STATIC / "chat.html")


app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# ---------------------------------------------------------------------------
# WebSocket helpers
# ---------------------------------------------------------------------------

async def send_msg(ws: WebSocket, msg_type: str, **kwargs):
    await ws.send_json({"type": msg_type, **kwargs})


async def send_text(ws: WebSocket, content: str):
    await send_msg(ws, "message", role="assistant", content=content)


async def send_interview(ws: WebSocket, questions: list[str]):
    await send_msg(ws, "interview", questions=questions)


async def send_options(ws: WebSocket, question: str, options: list[dict], multi_select: bool = True):
    await send_msg(ws, "options", question=question, options=options, multi_select=multi_select)


async def send_progress(ws: WebSocket, dimension: str, label: str, status: str):
    await send_msg(ws, "progress", dimension=dimension, label=label, status=status)


async def send_report(ws: WebSocket, content: str):
    await send_msg(ws, "report", content=content)


async def send_error(ws: WebSocket, message: str):
    await send_msg(ws, "error", message=message)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _load_mock():
    from mock_data import (
        get_mock_meta,
        get_mock_dim_sample_map,
        DIM_DISPLAY_NAMES,
    )
    return get_mock_meta(), get_mock_dim_sample_map(), DIM_DISPLAY_NAMES


def _build_dim_sample_map(meta: dict) -> dict[str, str]:
    """Build dim_key -> sample_id mapping from meta samples."""
    from dimensions import resolve_sample_id
    mapping: dict[str, str] = {}
    for s in meta.get("samples", []):
        sid = s.get("sample_id", "")
        dim = resolve_sample_id(sid)
        if dim and dim not in mapping:
            mapping[dim] = sid
    return mapping


def _get_display_names() -> dict[str, str]:
    """Get dimension display names from registry or fallback."""
    try:
        from dimensions import get_registry
        reg = get_registry()
        return {k: v["config"]["dimension"]["display_name"] for k, v in reg.items()}
    except Exception:
        from mock_data import DIM_DISPLAY_NAMES
        return DIM_DISPLAY_NAMES


async def _run_dimension_mock(ws: WebSocket, session: SessionState, dim_key: str):
    """Run a single dimension analysis in mock mode."""
    from mock_data import get_mock_dimension_result, DIM_DISPLAY_NAMES
    label = DIM_DISPLAY_NAMES.get(dim_key, dim_key)
    await send_progress(ws, dim_key, label, "running")
    await asyncio.sleep(1.5)
    result = get_mock_dimension_result(dim_key)
    if result:
        session.all_results[dim_key] = result
        await send_progress(ws, dim_key, label, "done")
    else:
        await send_progress(ws, dim_key, label, "error")


async def _run_dimension_real(ws: WebSocket, session: SessionState, dim_key: str):
    """Run a single dimension via the real agent pipeline."""
    display_names = _get_display_names()
    label = display_names.get(dim_key, dim_key)
    sample_id = session.dim_sample_map.get(dim_key, "")
    await send_progress(ws, dim_key, label, "running")
    try:
        from graph import dimension_worker
        result = dimension_worker({"_dim_key": dim_key, "_sample_id": sample_id})
        dim_result = result["dimension_results"][0]
        session.all_results[dim_key] = dim_result
        status = "done" if dim_result.get("status") == "success" else "error"
        await send_progress(ws, dim_key, label, status)
    except Exception as e:
        logger.error("dimension %s error: %s", dim_key, e)
        await send_progress(ws, dim_key, label, "error")


async def handle_greeting(ws: WebSocket, session: SessionState):
    """Send greeting and transition to WAIT_DESCRIPTION."""
    name = session.user_meta.get("name", "用户")
    await send_text(
        ws,
        f"您好{name}，我是您的精准健康管理助手。您今天有什么健康方面的关注吗？"
    )
    session.state = ChatState.WAIT_DESCRIPTION


async def handle_description(ws: WebSocket, session: SessionState, text: str):
    """User described symptoms -> send interview questions."""
    session.symptom_text = text
    session.state = ChatState.HEALTH_INTERVIEW

    questions = [
        "这些症状大概持续多久了？是近几周还是已经好几个月？",
        "您平时的饮食和作息习惯怎么样？比如是否经常应酬饮酒、加班熬夜？",
        "家里直系亲属有没有糖尿病、心血管疾病或肿瘤方面的病史？",
    ]
    await send_text(ws, "了解了，为了更准确地评估，我想先了解几个问题：")
    await send_interview(ws, questions)
    session.state = ChatState.WAIT_INTERVIEW_ANSWER


async def handle_interview_answer(ws: WebSocket, session: SessionState, answers: list[str]):
    """Process interview answers -> analyze symptoms -> suggest dimensions."""
    session.interview_answers = answers
    full_context = session.symptom_text + " " + " ".join(answers)

    from mock_data import map_symptoms_to_dimensions, DIM_DISPLAY_NAMES
    available = set(session.dim_sample_map.keys())
    recommended = map_symptoms_to_dimensions(full_context, available)

    # Filter out already analyzed
    recommended = [d for d in recommended if d not in session.analyzed_dims]

    if not recommended:
        recommended = [d for d in ["aging", "cd", "dr"] if d in available and d not in session.analyzed_dims]

    session.pending_dims = recommended
    session.state = ChatState.SUGGEST_DIMS
    await _send_dimension_suggestion(ws, session, recommended)


async def _send_dimension_suggestion(ws: WebSocket, session: SessionState, dims: list[str]):
    """Format and send dimension recommendation."""
    from mock_data import DIM_DISPLAY_NAMES

    # Build recommendation text with reasons
    dim_reasons = {
        "aging": "持续疲劳和睡眠问题可能提示生物年龄加速",
        "cd": "消化不适和腹胀与肠道菌群平衡密切相关",
        "dr": "结合家族糖尿病史，需评估代谢和心血管方向的风险水平",
        "my": "评估黏膜和系统免疫功能是否受到影响",
        "sw": "排查是否存在延迟型食物过敏导致的消化症状",
        "yc": "了解您的营养代谢能力和用药代谢特点",
        "zl": "通过ctDNA液体活检排查肿瘤风险",
        "gm": "检测IgE介导的即刻型过敏反应",
        "zm": "排查自身免疫性疾病可能",
    }

    lines = ["感谢您的信息。结合您的症状、生活习惯和家族史，建议从以下维度进行健康风险评估：\n"]
    options = []
    for d in dims:
        label = DIM_DISPLAY_NAMES.get(d, d)
        reason = dim_reasons.get(d, "")
        lines.append(f"- **{label}** — {reason}")
        options.append({"key": d, "label": label, "reason": reason})

    lines.append("\n> 注意：以上为风险评估，不构成临床诊断。是否开始分析？")
    await send_text(ws, "\n".join(lines))
    await send_options(ws, "推荐检测维度", options, multi_select=True)
    session.state = ChatState.WAIT_CONFIRM


async def handle_confirm(ws: WebSocket, session: SessionState, value: bool):
    """User confirmed -> run dimensions."""
    if not value:
        await send_text(ws, "好的，如果您有其他健康方面的关注，随时告诉我。")
        session.state = ChatState.WAIT_DESCRIPTION
        return

    await _run_round(ws, session, session.pending_dims)


async def handle_select(ws: WebSocket, session: SessionState, selected: list[str]):
    """User manually selected dimensions -> run them."""
    available = set(session.dim_sample_map.keys())
    valid = [d for d in selected if d in available and d not in session.analyzed_dims]
    if not valid:
        await send_text(ws, "所选维度已分析完毕或暂无对应样本数据。您还有其他想了解的吗？")
        session.state = ChatState.WAIT_DESCRIPTION
        return

    session.pending_dims = valid
    await _run_round(ws, session, valid)


async def _run_round(ws: WebSocket, session: SessionState, dims: list[str]):
    """Execute a round of dimension analyses."""
    session.state = ChatState.RUNNING
    session.round_number += 1

    for dim_key in dims:
        if _mock_mode:
            await _run_dimension_mock(ws, session, dim_key)
        else:
            await _run_dimension_real(ws, session, dim_key)
        session.analyzed_dims.append(dim_key)

    session.state = ChatState.ROUND_RESULT
    await _send_round_result(ws, session, dims)


async def _send_round_result(ws: WebSocket, session: SessionState, dims: list[str]):
    """Send results for the current round + interpretation."""
    from mock_data import ROUND_INTERPRETATIONS

    # Collect results for this round
    sections = []
    for d in dims:
        r = session.all_results.get(d)
        if r and r.get("data"):
            sections.append(r["data"])

    if sections:
        await send_text(ws, "\n\n---\n\n".join(sections))

    # Send round interpretation
    round_key = f"round{session.round_number}"
    interp = ROUND_INTERPRETATIONS.get(round_key)
    if interp:
        await send_text(ws, interp)

    # Check if all available dims are analyzed
    available = set(session.dim_sample_map.keys())
    remaining = available - set(session.analyzed_dims)
    if not remaining:
        await _send_final_report(ws, session)
    else:
        session.state = ChatState.WAIT_DESCRIPTION


async def _send_final_report(ws: WebSocket, session: SessionState):
    """Generate and send comprehensive report via synthesize_node or mock fallback."""
    session.state = ChatState.FINAL_REPORT

    if _mock_mode:
        from mock_data import FINAL_REPORT
        await send_report(ws, FINAL_REPORT)
    else:
        try:
            from supervisor import synthesize_node
            # Build state compatible with synthesize_node
            dim_results = []
            for dim_key, r in session.all_results.items():
                dim_results.append({
                    "dimension_key": dim_key,
                    "sample_id": session.dim_sample_map.get(dim_key, ""),
                    "status": r.get("status", "unknown"),
                    "data": r.get("data", ""),
                    "error": r.get("error", ""),
                })
            synth_state = {
                "user_sample_id": next(iter(session.dim_sample_map.values()), ""),
                "user_meta": session.user_meta,
                "dimension_results": dim_results,
            }
            result = synthesize_node(synth_state)
            await send_report(ws, result.get("synthesized_report", "报告生成失败"))
        except Exception as e:
            logger.error("synthesize_node error: %s", e)
            from mock_data import FINAL_REPORT
            await send_report(ws, FINAL_REPORT)

    session.state = ChatState.DONE


async def handle_followup(ws: WebSocket, session: SessionState, text: str):
    """Handle follow-up message: either symptom-based or request for final report."""
    if any(kw in text for kw in ["综合报告", "总结", "全部结果", "完整报告"]):
        await _send_final_report(ws, session)
        return

    # Check for direct dimension requests
    from mock_data import map_symptoms_to_dimensions
    available = set(session.dim_sample_map.keys())
    new_dims = map_symptoms_to_dimensions(text, available)
    new_dims = [d for d in new_dims if d not in session.analyzed_dims]

    if new_dims:
        session.pending_dims = new_dims
        await _send_dimension_suggestion(ws, session, new_dims)
    else:
        # Try broader matching or suggest remaining
        remaining = [d for d in available if d not in session.analyzed_dims]
        if remaining:
            session.pending_dims = remaining
            await _send_dimension_suggestion(ws, session, remaining)
        else:
            await _send_final_report(ws, session)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session = SessionState()

    try:
        # Initialize session
        if _mock_mode:
            meta, dim_map, _ = _load_mock()
            session.user_meta = meta
            session.dim_sample_map = dim_map
        else:
            # Real mode: fetch meta from API, build dim→sample mapping
            try:
                from skills.extract_meta import MetaExtractor
                ext = MetaExtractor()
                # user_id could come from query params in a full implementation
                user_id = ws.query_params.get("user_id", "")
                if not user_id:
                    await send_error(ws, "Real mode requires ?user_id= parameter.")
                    await ws.close()
                    return
                meta = ext.fetch_metadata(user_id)
                session.user_meta = meta
                session.dim_sample_map = _build_dim_sample_map(meta)
            except Exception as e:
                logger.error("Failed to init real session: %s", e)
                await send_error(ws, f"初始化失败: {e}")
                await ws.close()
                return

        # Send greeting
        await handle_greeting(ws, session)

        # Main loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(ws, "Invalid JSON")
                continue

            msg_type = msg.get("type", "message")

            if session.state == ChatState.WAIT_DESCRIPTION:
                if msg_type == "message":
                    # After at least one round, treat as follow-up (not new description)
                    if session.analyzed_dims:
                        await handle_followup(ws, session, msg.get("content", ""))
                    else:
                        await handle_description(ws, session, msg.get("content", ""))
                elif msg_type == "select":
                    await handle_select(ws, session, msg.get("selected", []))

            elif session.state == ChatState.WAIT_INTERVIEW_ANSWER:
                if msg_type == "interview":
                    await handle_interview_answer(ws, session, msg.get("answers", []))
                elif msg_type == "message":
                    # Treat single message as combined answer
                    await handle_interview_answer(ws, session, [msg.get("content", "")])

            elif session.state == ChatState.WAIT_CONFIRM:
                if msg_type == "confirm":
                    await handle_confirm(ws, session, msg.get("value", True))
                elif msg_type == "select":
                    await handle_select(ws, session, msg.get("selected", []))
                elif msg_type == "message":
                    content = msg.get("content", "").strip().lower()
                    if content in ("是", "好", "确认", "开始", "yes", "ok"):
                        await handle_confirm(ws, session, True)
                    else:
                        await handle_confirm(ws, session, False)

            elif session.state == ChatState.ROUND_RESULT:
                if msg_type == "message":
                    await handle_followup(ws, session, msg.get("content", ""))
                elif msg_type == "select":
                    await handle_select(ws, session, msg.get("selected", []))

            elif session.state == ChatState.DONE:
                await send_text(ws, "本次健康评估已完成。如需进一步咨询，请开启新的对话。")

            else:
                await send_text(ws, "请稍候，系统正在处理中...")

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await send_error(ws, str(e))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DigitalMe Health Chat Server")
    parser.add_argument("--mock", action="store_true", default=True, help="Run in mock mode (default)")
    parser.add_argument("--real", action="store_true", help="Run in real mode (requires API access)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    args = parser.parse_args()

    if args.real:
        set_mock_mode(False)
    else:
        set_mock_mode(True)

    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
