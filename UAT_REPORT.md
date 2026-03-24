# DigitalMe UAT Test Report

| Item | Value |
|------|-------|
| Date | 2026-03-23 19:28:32 |
| Target | http://localhost:8765 |
| Browser | Chromium (headless) |
| Viewport | 430x932 (mobile) |
| Total Tests | 20 |
| Passed | 20 |
| Failed | 0 |
| Total Duration | 258.3s |

## Test Results

| ID | Test | Status | Duration |
|----|------|--------|----------|
| T01 | Page load & layout | PASS | 1393ms |
| T02 | WebSocket greeting | PASS | 1219ms |
| T03 | Symptom input & interview card | PASS | 1206ms |
| T04 | Interview answer & dimension recommendation | PASS | 1513ms |
| T05 | Chips pre-selected & toggle | PASS | 2697ms |
| T06 | Confirm & progress indicators | PASS | 10450ms |
| T07 | Round 1 results display | PASS | 12867ms |
| T08 | Follow-up input & round 2 recommendation | PASS | 15980ms |
| T09 | Round 2 confirm & progress | PASS | 23523ms |
| T10 | Round 3 flow | PASS | 38590ms |
| T11 | Final report card | PASS | 38487ms |
| T12 | DONE state reply | PASS | 42065ms |
| T13 | Demo mode toggle & auto-playback | PASS | 4150ms |
| T14 | Demo pause at wait_for_input | PASS | 4169ms |
| T15 | Demo user interaction resume | PASS | 8186ms |
| T16 | Responsive layout (mobile viewport) | PASS | 1207ms |
| T17 | Markdown rendering in messages | PASS | 2071ms |
| T18 | Empty input ignored | PASS | 1695ms |
| T19 | Multiple progress cards coexist | PASS | 8366ms |
| T20 | Report card key sections | PASS | 38506ms |

## Screenshots

All screenshots saved to: `/Users/kangfan/Project/digitalme/uat_screenshots/`

- `T01`: `uat_screenshots/T01_*.png`
- `T02`: `uat_screenshots/T02_*.png`
- `T03`: `uat_screenshots/T03_*.png`
- `T04`: `uat_screenshots/T04_*.png`
- `T05`: `uat_screenshots/T05_*.png`
- `T06`: `uat_screenshots/T06_*.png`
- `T07`: `uat_screenshots/T07_*.png`
- `T08`: `uat_screenshots/T08_*.png`
- `T09`: `uat_screenshots/T09_*.png`
- `T10`: `uat_screenshots/T10_*.png`
- `T11`: `uat_screenshots/T11_*.png`
- `T12`: `uat_screenshots/T12_*.png`
- `T13`: `uat_screenshots/T13_*.png`
- `T14`: `uat_screenshots/T14_*.png`
- `T15`: `uat_screenshots/T15_*.png`
- `T16`: `uat_screenshots/T16_*.png`
- `T17`: `uat_screenshots/T17_*.png`
- `T18`: `uat_screenshots/T18_*.png`
- `T19`: `uat_screenshots/T19_*.png`
- `T20`: `uat_screenshots/T20_*.png`

## Test Coverage

| Category | Tests | Coverage |
|----------|-------|----------|
| Page Load & Layout | T01, T16 | Header, chat area, input, mobile responsive |
| WebSocket Communication | T02, T18 | Greeting, empty input handling |
| Symptom Input Flow | T03, T04, T05 | Interview card, recommendations, chip selection |
| Analysis Flow | T06, T07, T08, T09, T10 | Progress indicators, 3-round analysis |
| Report Generation | T11, T12, T20 | Final report, DONE state, report content |
| Demo Mode | T13, T14, T15 | Toggle, auto-play, pause/resume |
| UI Components | T05, T17, T19 | Chips, markdown rendering, progress cards |
