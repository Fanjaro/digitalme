"""Phase 7 - Test 42: Tool unit tests using local _data.json files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "skills" / "data"


def _load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


# --- CD: appendix_sections ---
def test_cd_extraction():
    data = _load_json("肠道微生物_data.json")
    assert data["sample_id"] == "CD888888"
    assert "appendix" in data
    assert "sections" in data["appendix"]
    sections = data["appendix"]["sections"]
    assert isinstance(sections, list)
    assert len(sections) > 0
    assert "title" in sections[0]


# --- PF: data_fields.appendixList microbiome ---
def test_pf_extraction():
    data = _load_json("皮肤微生物数据_data.json")
    assert data["sample_id"] == "PF888888"
    al = data["data_fields"]["appendixList"]
    assert "beneficialData" in al
    assert "conditionalPathogenData" in al
    assert "harmfulData" in al
    assert len(al["beneficialData"]) > 0
    item = al["beneficialData"][0]
    assert all(k in item for k in ["cnName", "name", "abundance", "signalValue"])


# --- ZL: data_fields.ctDna ---
def test_zl_extraction():
    data = _load_json("肿瘤ct-DNA_data.json")
    assert data["sample_id"] == "ZL888888"
    df = data["data_fields"]
    assert "ctDna" in df
    assert "mutations" in df
    ct = df["ctDna"]
    assert "mutationCount" in ct
    assert "mutationFrequency" in ct
    assert "tumorRisk" in ct
    assert isinstance(df["mutations"], list)
    assert len(df["mutations"]) > 0
    mut = df["mutations"][0]
    assert all(k in mut for k in ["mutationSite", "detectionFrequency", "geneFunction"])


# --- MY: appendixTable ---
def test_my_extraction():
    data = _load_json("抗体免疫力_data.json")
    assert data["sample_id"] == "MY888888"
    assert "appendixTable" in data
    table = data["appendixTable"]
    assert isinstance(table, list)
    assert len(table) > 0
    row = table[0]
    assert all(k in row for k in ["name", "uniprot", "value", "refRange"])


# --- ZM: appendixTable ---
def test_zm_extraction():
    data = _load_json("自身免疫抗体_data.json")
    assert data["sample_id"] == "ZM888888"
    assert "appendixTable" in data
    table = data["appendixTable"]
    assert isinstance(table, list)
    assert len(table) > 0


# --- AGING (KS): data.aging ---
def test_aging_extraction():
    data = _load_json("衰老数据_data.json")
    assert data["sample_id"] == "KS888888"
    assert "data" in data
    aging = data["data"]["aging"]
    assert isinstance(aging, dict)
    assert len(aging) > 0
    # Check one mechanism
    mech = next(iter(aging.values()))
    assert "pred_quantile" in mech
    assert "pred_raw" in mech
    assert "uniprot" in mech
    assert "value" in mech
    assert "lower" in mech
    assert "upper" in mech
    assert len(mech["value"]) == len(mech["lower"]) == len(mech["upper"])


# --- GM: data.aging + report_type=ige ---
def test_gm_extraction():
    data = _load_json("过敏原组份IgE检测_data.json")
    assert data["sample_id"] == "GM888888"
    assert data["report_type"] == "ige"
    assert "data" in data
    aging = data["data"]["aging"]
    assert isinstance(aging, dict)
    assert len(aging) > 0


# --- SW: data.chronic_immune_intolerance ---
def test_sw_extraction():
    data = _load_json("食物不耐受IgG检测_data.json")
    assert data["sample_id"] == "SW888888"
    assert data["report_type"] == "IgGFood"
    cii = data["data"]["chronic_immune_intolerance"]
    assert isinstance(cii, dict)
    assert len(cii) > 0
    # Check one food category
    cat = next(iter(cii.values()))
    assert "uniprot" in cat
    assert "value" in cat


# --- DR: data_fields.unscramble ---
def test_dr_extraction():
    data = _load_json("5大疾病数据_data.json")
    assert data["sample_id"] == "DR888888"
    unscramble = data["data_fields"]["unscramble"]
    for key in ["cancer", "cardiovascular", "digestive_system", "infection", "metabolic"]:
        assert key in unscramble, f"Missing {key} in unscramble"
        assert isinstance(unscramble[key], list)


# --- YC: data_fields.detection ---
def test_yc_extraction():
    data = _load_json("体细胞遗传突变_data.json")
    assert data["sample_id"] == "YC888888"
    detection = data["data_fields"]["detection"]
    assert "ability" in detection
    assert isinstance(detection["ability"], list)
    assert len(detection["ability"]) > 0
    item = detection["ability"][0]
    assert "category" in item
    assert "items" in item


# --- SMX: data_fields.appendixList bacterial ---
def test_smx_extraction():
    data = _load_json("女性私密微生物_data.json")
    assert data["sample_id"] == "SMX888888"
    al = data["data_fields"]["appendixList"]
    for key in ["bacterial_pathogen", "fungal_pathogen", "opportunistic", "parasitic_pathogen"]:
        assert key in al, f"Missing {key} in SMX appendixList"
        assert isinstance(al[key], list)
    # Check pathogen entry structure
    entry = al["bacterial_pathogen"][0]
    assert all(k in entry for k in ["cnName", "detectionResult", "clinicalNote"])


# --- SMY: data_fields.appendixList bacterial + commensal ---
def test_smy_extraction():
    data = _load_json("男性私密微生物_data.json")
    assert data["sample_id"] == "SMY888888"
    al = data["data_fields"]["appendixList"]
    for key in ["bacterial_pathogen", "fungal_pathogen", "opportunistic", "parasitic_pathogen"]:
        assert key in al, f"Missing {key} in SMY appendixList"
    # SMY-specific: commensal category
    assert "commensal" in al, "SMY should have 'commensal' category in appendixList"
    assert isinstance(al["commensal"], list)


# --- Cross-check: structure_type detection matches actual data ---
def test_structure_type_detection():
    from generator import analyze_data_structure

    cases = [
        ("肠道微生物_data.json", "appendix_sections"),
        ("皮肤微生物数据_data.json", "data_fields_appendixList_microbiome"),
        ("肿瘤ct-DNA_data.json", "data_fields_ctdna"),
        ("抗体免疫力_data.json", "appendix_table"),
        ("自身免疫抗体_data.json", "appendix_table"),
        ("衰老数据_data.json", "v1_aging"),
        ("过敏原组份IgE检测_data.json", "v1_aging_ige"),
        ("食物不耐受IgG检测_data.json", "v1_food_intolerance"),
        ("5大疾病数据_data.json", "data_fields_unscramble"),
        ("体细胞遗传突变_data.json", "data_fields_detection"),
        ("女性私密微生物_data.json", "data_fields_appendixList_bacterial"),
        ("男性私密微生物_data.json", "data_fields_appendixList_bacterial"),
    ]
    for filename, expected_type in cases:
        data = _load_json(filename)
        result = analyze_data_structure(data)
        assert result["structure_type"] == expected_type, \
            f"{filename}: expected {expected_type}, got {result['structure_type']}"


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
