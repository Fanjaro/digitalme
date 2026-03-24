"""Phase 7 - Test 41: Registry tests."""
import importlib
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dimensions import get_registry, get_prefix_map, resolve_sample_id, build_agent


def test_registry_returns_12_dimensions():
    reg = get_registry()
    assert len(reg) == 12, f"Expected 12 dimensions, got {len(reg)}"


def test_registry_keys():
    reg = get_registry()
    expected = {"cd", "pf", "zl", "my", "zm", "aging", "gm", "sw", "dr", "yc", "smx", "smy"}
    assert set(reg.keys()) == expected


def test_registry_config_has_required_fields():
    reg = get_registry()
    for key, info in reg.items():
        cfg = info["config"]
        assert "dimension" in cfg, f"{key}: missing dimension"
        assert "key" in cfg["dimension"], f"{key}: missing dimension.key"
        assert cfg["dimension"]["key"] == key, f"{key}: dimension.key mismatch"
        assert "sample_id" in cfg, f"{key}: missing sample_id"
        assert "prefixes" in cfg["sample_id"], f"{key}: missing prefixes"
        assert "api" in cfg, f"{key}: missing api"
        assert "version" in cfg["api"], f"{key}: missing api.version"
        assert "data_extraction" in cfg, f"{key}: missing data_extraction"
        assert "structure_type" in cfg["data_extraction"], f"{key}: missing structure_type"


def test_prefix_map_has_15_entries():
    pm = get_prefix_map()
    assert len(pm) == 15, f"Expected 15 prefixes (KS+KS1027+TY→aging, SW+IGGFOOD→sw), got {len(pm)}"


def test_prefix_map_correct_mappings():
    pm = get_prefix_map()
    expected = {
        "CD": "cd", "PF": "pf", "ZL": "zl", "MY": "my", "ZM": "zm",
        "KS": "aging", "KS1027": "aging", "TY": "aging",
        "GM": "gm", "SW": "sw", "IGGFOOD": "sw",
        "DR": "dr", "YC": "yc", "SMX": "smx", "SMY": "smy",
    }
    assert pm == expected


def test_resolve_sample_id_known():
    cases = [
        ("CD888888", "cd"),
        ("PF999999", "pf"),
        ("ZL888888", "zl"),
        ("MY888888", "my"),
        ("ZM888888", "zm"),
        ("KS901068", "aging"),
        ("TY888888", "aging"),
        ("GM888888", "gm"),
        ("SW888888", "sw"),
        ("DR888888", "dr"),
        ("YC888888", "yc"),
        ("SMX888888", "smx"),
        ("SMY888888", "smy"),
    ]
    for sid, expected in cases:
        result = resolve_sample_id(sid)
        assert result == expected, f"resolve({sid}) = {result}, expected {expected}"


def test_resolve_long_prefix():
    assert resolve_sample_id("KS1027888888") == "aging"
    assert resolve_sample_id("IgGFood888888") == "sw"


def test_resolve_sample_id_unknown():
    assert resolve_sample_id("UNKNOWN123") is None
    assert resolve_sample_id("XX999") is None
    assert resolve_sample_id("") is None


def test_each_dimension_module_has_build_agent():
    reg = get_registry()
    for key, info in reg.items():
        mod = importlib.import_module(info["module_path"])
        assert hasattr(mod, "build_agent"), f"{key} missing build_agent"
        assert hasattr(mod, "CONFIG"), f"{key} missing CONFIG"
        assert callable(mod.build_agent), f"{key} build_agent not callable"


def test_api_version_correct():
    reg = get_registry()
    v1_dims = {"aging", "gm", "sw"}
    for key, info in reg.items():
        version = info["config"]["api"]["version"]
        if key in v1_dims:
            assert version == "v1", f"{key} should be v1, got {version}"
        else:
            assert version == "v2", f"{key} should be v2, got {version}"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
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
