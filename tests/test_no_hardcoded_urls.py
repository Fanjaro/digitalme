"""Verify no hardcoded internal API URLs remain in dimension tools."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DIMENSIONS_DIR = Path(__file__).parent.parent / "dimensions"


def test_no_hardcoded_urls_in_tools():
    for tools_file in sorted(DIMENSIONS_DIR.glob("*/tools.py")):
        content = tools_file.read_text()
        assert "10.1.20.128" not in content, (
            f"{tools_file.relative_to(DIMENSIONS_DIR.parent)} contains hardcoded URL"
        )


def test_no_hardcoded_urls_in_generator():
    gen_file = Path(__file__).parent.parent / "generator.py"
    content = gen_file.read_text()
    assert "10.1.20.128" not in content, "generator.py contains hardcoded URL"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {t.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {t.__name__} — {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
