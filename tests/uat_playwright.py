#!/usr/bin/env python3
"""
DigitalMe UAT — Playwright end-to-end browser tests.

Covers:
  T01  Page load & layout
  T02  WebSocket greeting
  T03  Symptom input & interview card
  T04  Interview answer & dimension recommendation
  T05  Chips pre-selected & toggle
  T06  Confirm & progress indicators
  T07  Round 1 results display
  T08  Follow-up input & round 2 recommendation
  T09  Round 2 confirm & progress
  T10  Round 3 flow
  T11  Final report card
  T12  DONE state reply
  T13  Demo mode toggle & auto-playback
  T14  Demo pause at wait_for_input
  T15  Demo user interaction resume
  T16  Responsive layout (mobile viewport)
  T17  Markdown rendering in messages
  T18  Error display for empty input
  T19  Multiple progress cards coexist
  T20  Report card contains key sections
"""

import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright, expect, Page, Locator

BASE_URL = os.environ.get("UAT_BASE_URL", "http://localhost:8765")
SCREENSHOT_DIR = Path(__file__).parent.parent / "uat_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    id: str
    name: str
    status: str = "SKIP"  # PASS / FAIL / SKIP
    duration_ms: int = 0
    error: str = ""
    screenshot: str = ""


results: list[TestResult] = []


def screenshot(page: Page, name: str) -> str:
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=str(path))
    return str(path)


def run_test(test_id: str, test_name: str, fn, page: Page, **kwargs):
    """Run a single test, capture result."""
    r = TestResult(id=test_id, name=test_name)
    t0 = time.time()
    try:
        fn(page, **kwargs)
        r.status = "PASS"
    except Exception as e:
        r.status = "FAIL"
        r.error = str(e)
        try:
            r.screenshot = screenshot(page, f"{test_id}_FAIL")
        except Exception:
            pass
    r.duration_ms = int((time.time() - t0) * 1000)
    results.append(r)
    print(f"  [{r.status}] {test_id}: {test_name} ({r.duration_ms}ms)")
    return r.status == "PASS"


# ---------------------------------------------------------------------------
# Helper: wait for WebSocket messages to arrive
# ---------------------------------------------------------------------------

def wait_for_msg(page: Page, selector: str, timeout: int = 8000):
    """Wait for an element matching selector to appear."""
    page.wait_for_selector(selector, timeout=timeout)


def count_elements(page: Page, selector: str) -> int:
    return page.locator(selector).count()


def send_chat(page: Page, text: str):
    """Type into the chat input and press Enter."""
    inp = page.locator("#msgInput")
    inp.fill(text)
    inp.press("Enter")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def t01_page_load(page: Page):
    """T01: Page loads with header, chat area, input bar."""
    page.goto(BASE_URL, wait_until="networkidle")
    # Header
    header = page.locator(".header")
    expect(header).to_be_visible()
    expect(header).to_contain_text("DigitalMe")
    # Chat area
    expect(page.locator("#chatArea")).to_be_visible()
    # Input bar
    expect(page.locator("#msgInput")).to_be_visible()
    expect(page.locator("#sendBtn")).to_be_visible()
    # Demo toggle
    expect(page.locator("#demoToggle")).to_be_visible()
    screenshot(page, "T01_page_load")


def t02_ws_greeting(page: Page):
    """T02: WebSocket connects and server sends greeting with user name."""
    page.goto(BASE_URL, wait_until="networkidle")
    # Wait for greeting bubble
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    greeting = page.locator(".msg.assistant").first
    expect(greeting).to_contain_text("张")
    expect(greeting).to_contain_text("健康")
    screenshot(page, "T02_greeting")


def t03_symptom_and_interview(page: Page):
    """T03: User sends symptoms -> receives interview card with 3 questions."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    # Send symptoms
    send_chat(page, "最近总是感觉很累，消化不好，腹胀，睡眠差")
    # Wait for interview card
    wait_for_msg(page, ".interview-card", timeout=8000)
    # Should have 3 question items
    q_items = page.locator(".interview-card .q-item")
    assert q_items.count() == 3, f"Expected 3 questions, got {q_items.count()}"
    # Should have textarea
    expect(page.locator("#interviewAnswer")).to_be_visible()
    screenshot(page, "T03_interview_card")


def t04_interview_answer_and_recommendation(page: Page):
    """T04: Answer interview -> receive dimension recommendations with options card."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好，腹胀，睡眠差")
    wait_for_msg(page, ".interview-card", timeout=8000)
    # Fill interview answer
    page.locator("#interviewAnswer").fill("半年多了，应酬多，经常喝酒熬夜。父亲有糖尿病。")
    page.locator(".interview-card .submit-btn").click()
    # Wait for options card
    wait_for_msg(page, ".options-card", timeout=10000)
    chips = page.locator(".options-card .chip")
    assert chips.count() >= 2, f"Expected >=2 chips, got {chips.count()}"
    screenshot(page, "T04_recommendations")


def t05_chips_preselected_and_toggle(page: Page):
    """T05: Chips are pre-selected; clicking toggles selection."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    # All chips should have 'selected' class initially
    chips = page.locator(".options-card .chip")
    for i in range(chips.count()):
        assert "selected" in chips.nth(i).get_attribute("class"), f"Chip {i} not pre-selected"
    # Click first chip to deselect
    chips.first.click()
    assert "selected" not in chips.first.get_attribute("class"), "Chip should be deselected after click"
    # Click again to re-select
    chips.first.click()
    assert "selected" in chips.first.get_attribute("class"), "Chip should be re-selected after second click"
    screenshot(page, "T05_chips_toggle")


def t06_confirm_and_progress(page: Page):
    """T06: Confirm starts analysis -> progress cards appear (running then done)."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好，腹胀")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    # Click confirm
    page.locator(".confirm-btn.yes").click()
    # Wait for at least one progress card
    wait_for_msg(page, ".progress-card", timeout=5000)
    screenshot(page, "T06_progress_running")
    # Wait for analysis to complete (mock: ~1.5s per dim * 3 dims)
    page.wait_for_timeout(8000)
    # Should have progress cards with 'done' status
    done_icons = page.locator(".progress-card .icon.done")
    assert done_icons.count() >= 2, f"Expected >=2 done progress, got {done_icons.count()}"
    screenshot(page, "T06_progress_done")


def t07_round1_results(page: Page):
    """T07: After round 1, result messages appear with medical data tables."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好，腹胀")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    page.locator(".confirm-btn.yes").click()
    # Wait for round 1 results (progress + result messages)
    page.wait_for_timeout(10000)
    # Should have multiple assistant messages including results
    msgs = page.locator(".msg.assistant")
    assert msgs.count() >= 3, f"Expected >=3 assistant messages after round 1, got {msgs.count()}"
    # Check for table rendering (markdown tables become <table>)
    page_content = page.content()
    assert "<table" in page_content.lower(), "Expected rendered markdown tables in results"
    screenshot(page, "T07_round1_results")


def t08_followup_and_round2(page: Page):
    """T08: Follow-up question triggers new dimension recommendations."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    options_count_before = page.locator(".options-card").count()
    page.locator(".confirm-btn.yes").click()
    page.wait_for_timeout(10000)  # Wait for round 1 to complete
    # Send follow-up
    send_chat(page, "免疫力怎么样？吃的东西有问题吗？基因代谢能力有没有问题？")
    # Wait for new options card to appear
    page.wait_for_timeout(3000)
    options_cards = page.locator(".options-card")
    assert options_cards.count() > options_count_before, \
        f"Expected new options card, had {options_count_before}, now {options_cards.count()}"
    screenshot(page, "T08_round2_recommendation")


def t09_round2_progress(page: Page):
    """T09: Confirm round 2 -> see progress for new dimensions."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    page.locator(".confirm-btn.yes").click()
    page.wait_for_timeout(10000)
    # Follow-up
    send_chat(page, "免疫力怎么样？吃的东西有问题吗？基因代谢能力有没有问题？")
    page.wait_for_timeout(3000)
    # Click the enabled confirm button (round 2's fresh button)
    page.locator(".confirm-btn.yes:not([disabled])").click()
    page.wait_for_timeout(8000)
    # Count total progress cards (round 1 + round 2)
    progress = page.locator(".progress-card")
    assert progress.count() >= 5, f"Expected >=5 total progress cards, got {progress.count()}"
    screenshot(page, "T09_round2_progress")


def _run_3_rounds(page: Page):
    """Helper: execute full 3-round flow, returns after round 3 completes."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    # Symptoms
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    # Round 1: confirm
    page.locator(".confirm-btn.yes").click()
    page.wait_for_timeout(10000)
    # Round 2: follow-up
    send_chat(page, "免疫力怎么样？吃的东西有问题吗？基因代谢能力有没有问题？")
    page.wait_for_timeout(3000)
    page.locator(".confirm-btn.yes:not([disabled])").click()
    page.wait_for_timeout(10000)
    # Round 3: tumor + allergy
    send_chat(page, "帮我也查一下肿瘤和过敏方面")
    page.wait_for_timeout(3000)
    enabled_btns = page.locator(".confirm-btn.yes:not([disabled])")
    if enabled_btns.count() > 0:
        enabled_btns.first.click()
    page.wait_for_timeout(10000)


def t10_round3_flow(page: Page):
    """T10: Third round of analysis (tumor + allergy)."""
    _run_3_rounds(page)
    # Should have progress cards for round 3 dims
    progress = page.locator(".progress-card")
    assert progress.count() >= 8, f"Expected >=8 total progress cards for 3 rounds, got {progress.count()}"
    screenshot(page, "T10_round3")


def t11_final_report(page: Page):
    """T11: Request final report -> report card appears."""
    _run_3_rounds(page)
    # Request report
    send_chat(page, "给我综合报告")
    wait_for_msg(page, ".report-card", timeout=10000)
    report = page.locator(".report-card")
    assert report.count() >= 1, "Expected at least 1 report card"
    screenshot(page, "T11_final_report")


def t12_done_state(page: Page):
    """T12: After final report, sending a message gets DONE state reply."""
    _run_3_rounds(page)
    send_chat(page, "给我综合报告")
    wait_for_msg(page, ".report-card", timeout=10000)
    page.wait_for_timeout(1000)
    # Count messages before
    msg_count_before = page.locator(".msg.assistant").count()
    send_chat(page, "还有别的吗")
    page.wait_for_timeout(2000)
    msg_count_after = page.locator(".msg.assistant").count()
    assert msg_count_after > msg_count_before, "Expected a DONE state reply"
    last_msg = page.locator(".msg.assistant").last
    expect(last_msg).to_contain_text("完成")
    screenshot(page, "T12_done_state")


def t13_demo_mode_toggle(page: Page):
    """T13: Toggle demo mode -> auto-playback begins with greeting."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    # Toggle demo on
    page.locator("#demoToggle").click()
    page.wait_for_timeout(3000)
    # Chat area should have been cleared and demo greeting loaded
    msgs = page.locator(".msg.assistant")
    assert msgs.count() >= 1, "Expected at least 1 assistant message in demo mode"
    first_msg = msgs.first
    expect(first_msg).to_contain_text("张")
    screenshot(page, "T13_demo_mode")


def t14_demo_pause(page: Page):
    """T14: Demo pauses at wait_for_input items."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    page.locator("#demoToggle").click()
    page.wait_for_timeout(3000)
    # After greeting, demo should pause (next item is user message with wait_for_input)
    # Count messages — should be exactly 1 (greeting only, not auto-proceeding)
    assistant_msgs = page.locator(".msg.assistant")
    user_msgs = page.locator(".msg.user")
    assert assistant_msgs.count() == 1, f"Expected 1 assistant msg (paused), got {assistant_msgs.count()}"
    assert user_msgs.count() == 0, f"Expected 0 user msgs (paused), got {user_msgs.count()}"
    screenshot(page, "T14_demo_paused")


def t15_demo_user_resume(page: Page):
    """T15: User typing in demo mode resumes playback."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    page.locator("#demoToggle").click()
    page.wait_for_timeout(3000)
    # Type symptom to resume
    send_chat(page, "最近总是感觉很累")
    page.wait_for_timeout(4000)
    # Demo should have resumed: interview card or more messages
    interview_or_msgs = page.locator(".interview-card").count() + page.locator(".msg.assistant").count()
    assert interview_or_msgs >= 2, f"Expected demo to resume with more content, got {interview_or_msgs}"
    screenshot(page, "T15_demo_resumed")


def t16_responsive_mobile(page: Page):
    """T16: Verify mobile viewport renders correctly."""
    page.set_viewport_size({"width": 375, "height": 812})  # iPhone X
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    # Verify layout still works
    expect(page.locator(".header")).to_be_visible()
    expect(page.locator("#chatArea")).to_be_visible()
    expect(page.locator("#msgInput")).to_be_visible()
    # Chat area should fill the screen properly
    chat_box = page.locator("#chatArea").bounding_box()
    assert chat_box["width"] <= 375, f"Chat area wider than viewport: {chat_box['width']}"
    screenshot(page, "T16_mobile_view")


def t17_markdown_rendering(page: Page):
    """T17: Markdown in messages renders as HTML (bold, lists, etc.)."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    # The recommendation text should contain rendered markdown (bold, lists)
    page_html = page.content()
    assert "<strong>" in page_html or "<b>" in page_html, "Expected bold markdown rendering"
    assert "<li>" in page_html or "<ul>" in page_html, "Expected list markdown rendering"
    screenshot(page, "T17_markdown")


def t18_empty_input(page: Page):
    """T18: Pressing send with empty input does nothing."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    msg_count = page.locator(".msg").count()
    # Press enter with empty input
    page.locator("#msgInput").press("Enter")
    page.wait_for_timeout(500)
    assert page.locator(".msg").count() == msg_count, "Empty send should not add messages"
    screenshot(page, "T18_empty_input")


def t19_multiple_progress_cards(page: Page):
    """T19: Multiple progress cards coexist for different dimensions."""
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_msg(page, ".msg.assistant", timeout=5000)
    send_chat(page, "最近总是感觉很累，消化不好")
    wait_for_msg(page, ".interview-card", timeout=8000)
    page.locator("#interviewAnswer").fill("半年了，应酬多，父亲有糖尿病")
    page.locator(".interview-card .submit-btn").click()
    wait_for_msg(page, ".options-card", timeout=10000)
    page.locator(".confirm-btn.yes").click()
    # Wait for multiple progress cards
    page.wait_for_timeout(6000)
    progress = page.locator(".progress-card")
    assert progress.count() >= 3, f"Expected >=3 coexisting progress cards, got {progress.count()}"
    # Each should be a distinct dimension
    screenshot(page, "T19_multiple_progress")


def t20_report_content(page: Page):
    """T20: Report card contains key health management sections."""
    _run_3_rounds(page)
    send_chat(page, "给我综合报告")
    wait_for_msg(page, ".report-card", timeout=10000)
    report_text = page.locator(".report-card").inner_text()
    checks = [
        ("张明远", "Report should contain patient name"),
        ("饮食调整", "Report should contain diet adjustment section"),
        ("免责声明", "Report should contain disclaimer"),
        ("随访", "Report should contain follow-up plan"),
    ]
    for keyword, msg in checks:
        assert keyword in report_text, msg
    screenshot(page, "T20_report_content")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    print(f"\n{'='*60}")
    print(f"  DigitalMe UAT — Playwright E2E Tests")
    print(f"  Target: {BASE_URL}")
    print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    all_tests = [
        ("T01", "Page load & layout", t01_page_load),
        ("T02", "WebSocket greeting", t02_ws_greeting),
        ("T03", "Symptom input & interview card", t03_symptom_and_interview),
        ("T04", "Interview answer & dimension recommendation", t04_interview_answer_and_recommendation),
        ("T05", "Chips pre-selected & toggle", t05_chips_preselected_and_toggle),
        ("T06", "Confirm & progress indicators", t06_confirm_and_progress),
        ("T07", "Round 1 results display", t07_round1_results),
        ("T08", "Follow-up input & round 2 recommendation", t08_followup_and_round2),
        ("T09", "Round 2 confirm & progress", t09_round2_progress),
        ("T10", "Round 3 flow", t10_round3_flow),
        ("T11", "Final report card", t11_final_report),
        ("T12", "DONE state reply", t12_done_state),
        ("T13", "Demo mode toggle & auto-playback", t13_demo_mode_toggle),
        ("T14", "Demo pause at wait_for_input", t14_demo_pause),
        ("T15", "Demo user interaction resume", t15_demo_user_resume),
        ("T16", "Responsive layout (mobile viewport)", t16_responsive_mobile),
        ("T17", "Markdown rendering in messages", t17_markdown_rendering),
        ("T18", "Empty input ignored", t18_empty_input),
        ("T19", "Multiple progress cards coexist", t19_multiple_progress_cards),
        ("T20", "Report card key sections", t20_report_content),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for test_id, test_name, test_fn in all_tests:
            # Each test gets a fresh context/page to avoid state leakage
            context = browser.new_context(viewport={"width": 430, "height": 932})
            page = context.new_page()
            try:
                run_test(test_id, test_name, test_fn, page)
            finally:
                context.close()

        browser.close()

    # Summary
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    total = len(results)

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} PASS, {failed} FAIL")
    print(f"{'='*60}\n")

    # Generate report
    generate_report(results)
    return 0 if failed == 0 else 1


def generate_report(results: list[TestResult]):
    """Generate markdown UAT report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    total = len(results)
    total_ms = sum(r.duration_ms for r in results)

    lines = [
        f"# DigitalMe UAT Test Report",
        f"",
        f"| Item | Value |",
        f"|------|-------|",
        f"| Date | {now} |",
        f"| Target | {BASE_URL} |",
        f"| Browser | Chromium (headless) |",
        f"| Viewport | 430x932 (mobile) |",
        f"| Total Tests | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"| Total Duration | {total_ms/1000:.1f}s |",
        f"",
        f"## Test Results",
        f"",
        f"| ID | Test | Status | Duration |",
        f"|----|------|--------|----------|",
    ]

    for r in results:
        status_icon = "PASS" if r.status == "PASS" else "FAIL"
        lines.append(f"| {r.id} | {r.name} | {status_icon} | {r.duration_ms}ms |")

    # Failed details
    failed_tests = [r for r in results if r.status == "FAIL"]
    if failed_tests:
        lines.append("")
        lines.append("## Failed Test Details")
        lines.append("")
        for r in failed_tests:
            lines.append(f"### {r.id}: {r.name}")
            lines.append("")
            lines.append(f"**Error:**")
            lines.append(f"```")
            lines.append(r.error)
            lines.append(f"```")
            if r.screenshot:
                lines.append(f"**Screenshot:** `{r.screenshot}`")
            lines.append("")

    # Screenshots
    lines.append("")
    lines.append("## Screenshots")
    lines.append("")
    lines.append(f"All screenshots saved to: `{SCREENSHOT_DIR}/`")
    lines.append("")
    for r in results:
        if r.status == "PASS":
            ss_path = SCREENSHOT_DIR / f"{r.id}_{r.name.replace(' ', '_')}.png"
            # Use the actual screenshot path pattern
            lines.append(f"- `{r.id}`: `uat_screenshots/{r.id}_*.png`")

    lines.append("")
    lines.append("## Test Coverage")
    lines.append("")
    lines.append("| Category | Tests | Coverage |")
    lines.append("|----------|-------|----------|")
    lines.append("| Page Load & Layout | T01, T16 | Header, chat area, input, mobile responsive |")
    lines.append("| WebSocket Communication | T02, T18 | Greeting, empty input handling |")
    lines.append("| Symptom Input Flow | T03, T04, T05 | Interview card, recommendations, chip selection |")
    lines.append("| Analysis Flow | T06, T07, T08, T09, T10 | Progress indicators, 3-round analysis |")
    lines.append("| Report Generation | T11, T12, T20 | Final report, DONE state, report content |")
    lines.append("| Demo Mode | T13, T14, T15 | Toggle, auto-play, pause/resume |")
    lines.append("| UI Components | T05, T17, T19 | Chips, markdown rendering, progress cards |")
    lines.append("")

    report_path = Path(__file__).parent.parent / "UAT_REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Report saved to: {report_path}")


if __name__ == "__main__":
    sys.exit(main())
