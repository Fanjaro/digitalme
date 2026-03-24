"""L5: Server tests — WebSocket protocol, session state, mock mode."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from server import (
    SessionState, ChatState,
    handle_greeting, handle_description,
    handle_interview_answer, handle_confirm,
    handle_followup, handle_select,
    set_mock_mode,
)


def _make_ws():
    """Create a mock WebSocket that records sent messages."""
    ws = AsyncMock()
    ws._sent = []
    async def _send_json(data):
        ws._sent.append(data)
    ws.send_json = _send_json
    return ws


def _session_with_meta():
    """Create a session pre-loaded with mock data."""
    from mock_data import get_mock_meta, get_mock_dim_sample_map
    s = SessionState()
    s.user_meta = get_mock_meta()
    s.dim_sample_map = get_mock_dim_sample_map()
    return s


class TestGreeting:
    @pytest.mark.asyncio
    async def test_greeting_contains_name(self):
        ws = _make_ws()
        session = _session_with_meta()
        await handle_greeting(ws, session)
        assert session.state == ChatState.WAIT_DESCRIPTION
        assert any("张明远" in m.get("content", "") for m in ws._sent)

    @pytest.mark.asyncio
    async def test_greeting_message_type(self):
        ws = _make_ws()
        session = _session_with_meta()
        await handle_greeting(ws, session)
        assert ws._sent[0]["type"] == "message"
        assert ws._sent[0]["role"] == "assistant"


class TestDescription:
    @pytest.mark.asyncio
    async def test_description_triggers_interview(self):
        ws = _make_ws()
        session = _session_with_meta()
        session.state = ChatState.WAIT_DESCRIPTION
        await handle_description(ws, session, "最近总是感觉很累，消化不好")
        assert session.state == ChatState.WAIT_INTERVIEW_ANSWER
        types = [m["type"] for m in ws._sent]
        assert "interview" in types

    @pytest.mark.asyncio
    async def test_interview_has_3_questions(self):
        ws = _make_ws()
        session = _session_with_meta()
        await handle_description(ws, session, "疲劳")
        interview_msg = next(m for m in ws._sent if m["type"] == "interview")
        assert len(interview_msg["questions"]) == 3


class TestInterviewAnswer:
    @pytest.mark.asyncio
    async def test_answer_triggers_suggestion(self):
        ws = _make_ws()
        session = _session_with_meta()
        session.state = ChatState.WAIT_INTERVIEW_ANSWER
        session.symptom_text = "很累，消化不好"
        await handle_interview_answer(ws, session, ["半年了", "应酬多", "父亲有糖尿病"])
        assert session.state == ChatState.WAIT_CONFIRM
        types = [m["type"] for m in ws._sent]
        assert "options" in types


class TestConfirm:
    @pytest.mark.asyncio
    async def test_confirm_runs_analysis(self):
        set_mock_mode(True)
        ws = _make_ws()
        session = _session_with_meta()
        session.state = ChatState.WAIT_CONFIRM
        session.pending_dims = ["aging", "cd"]
        await handle_confirm(ws, session, True)
        # Should have progress messages
        progress_msgs = [m for m in ws._sent if m["type"] == "progress"]
        assert len(progress_msgs) >= 2
        assert "aging" in session.analyzed_dims
        assert "cd" in session.analyzed_dims

    @pytest.mark.asyncio
    async def test_deny_returns_to_wait(self):
        ws = _make_ws()
        session = _session_with_meta()
        session.state = ChatState.WAIT_CONFIRM
        session.pending_dims = ["aging"]
        await handle_confirm(ws, session, False)
        assert session.state == ChatState.WAIT_DESCRIPTION


class TestFollowup:
    @pytest.mark.asyncio
    async def test_followup_triggers_new_dims(self):
        set_mock_mode(True)
        ws = _make_ws()
        session = _session_with_meta()
        session.analyzed_dims = ["aging", "cd", "dr"]
        session.round_number = 1
        await handle_followup(ws, session, "免疫力怎么样？吃的东西有问题吗？")
        # Should suggest my/sw
        types = [m["type"] for m in ws._sent]
        assert "options" in types or "message" in types

    @pytest.mark.asyncio
    async def test_final_report_keyword(self):
        set_mock_mode(True)
        ws = _make_ws()
        session = _session_with_meta()
        session.analyzed_dims = list(session.dim_sample_map.keys())
        await handle_followup(ws, session, "给我综合报告")
        report_msgs = [m for m in ws._sent if m["type"] == "report"]
        assert len(report_msgs) == 1


class TestSelect:
    @pytest.mark.asyncio
    async def test_select_valid_dims(self):
        set_mock_mode(True)
        ws = _make_ws()
        session = _session_with_meta()
        await handle_select(ws, session, ["zl", "gm"])
        assert "zl" in session.analyzed_dims
        assert "gm" in session.analyzed_dims

    @pytest.mark.asyncio
    async def test_select_already_analyzed(self):
        ws = _make_ws()
        session = _session_with_meta()
        session.analyzed_dims = ["zl"]
        await handle_select(ws, session, ["zl"])
        assert session.state == ChatState.WAIT_DESCRIPTION


class TestFullStorylineE2E:
    """End-to-end 3-round storyline test in mock mode."""

    @pytest.mark.asyncio
    async def test_complete_3_round_flow(self):
        set_mock_mode(True)
        ws = _make_ws()
        session = _session_with_meta()

        # Round 0: Greeting
        await handle_greeting(ws, session)
        assert session.state == ChatState.WAIT_DESCRIPTION
        assert any("张明远" in m.get("content", "") for m in ws._sent)

        # Round 0: User describes symptoms
        ws._sent.clear()
        await handle_description(ws, session, "最近总是感觉很累，消化不好，腹胀，睡眠差")
        assert session.state == ChatState.WAIT_INTERVIEW_ANSWER

        # Round 0: User answers interview
        ws._sent.clear()
        await handle_interview_answer(
            ws, session,
            ["半年多了", "应酬多，经常喝酒熬夜", "父亲有糖尿病"]
        )
        assert session.state == ChatState.WAIT_CONFIRM
        assert len(session.pending_dims) > 0
        round1_dims = session.pending_dims.copy()

        # Round 1: Confirm → run aging/cd/dr
        ws._sent.clear()
        await handle_confirm(ws, session, True)
        assert session.round_number == 1
        for d in round1_dims:
            assert d in session.analyzed_dims
        progress_msgs = [m for m in ws._sent if m["type"] == "progress"]
        assert len(progress_msgs) >= len(round1_dims) * 2  # running + done each

        # Round 2: User asks about immunity / food / genetics
        ws._sent.clear()
        await handle_followup(ws, session, "免疫力怎么样？吃的东西有问题吗？基因代谢能力有没有问题？")
        assert session.state == ChatState.WAIT_CONFIRM
        round2_dims = session.pending_dims.copy()
        assert any(d in round2_dims for d in ["my", "sw", "yc"])

        # Round 2: Confirm
        ws._sent.clear()
        await handle_confirm(ws, session, True)
        assert session.round_number == 2
        for d in round2_dims:
            assert d in session.analyzed_dims

        # Round 3: User wants tumor + allergy checks
        ws._sent.clear()
        await handle_followup(ws, session, "帮我也查一下肿瘤和过敏方面")
        # Should suggest remaining dims (zl, gm, zm)
        if session.state == ChatState.WAIT_CONFIRM:
            round3_dims = session.pending_dims.copy()
            ws._sent.clear()
            await handle_confirm(ws, session, True)
        else:
            round3_dims = []  # already ran or went to report

        assert session.round_number >= 3 or session.state in (
            ChatState.DONE, ChatState.FINAL_REPORT, ChatState.WAIT_DESCRIPTION
        )

        # Verify all 9 dims analyzed
        available = set(session.dim_sample_map.keys())
        analyzed = set(session.analyzed_dims)
        assert analyzed == available, f"Missing: {available - analyzed}"

        # Request final report
        ws._sent.clear()
        await handle_followup(ws, session, "给我综合报告")
        report_msgs = [m for m in ws._sent if m["type"] == "report"]
        assert len(report_msgs) == 1
        assert "张明远" in report_msgs[0]["content"]
        assert session.state == ChatState.DONE


class TestMockConversationJson:
    def test_mock_conversation_loads(self):
        from pathlib import Path
        conv_path = Path(__file__).parent.parent / "static" / "mock_conversation.json"
        with open(conv_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 20

    def test_mock_conversation_has_all_types(self):
        from pathlib import Path
        conv_path = Path(__file__).parent.parent / "static" / "mock_conversation.json"
        with open(conv_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        types = {m["type"] for m in data}
        assert "message" in types
        assert "progress" in types
        assert "report" in types
        assert "options" in types
