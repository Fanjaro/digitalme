"""Auto-discovery registry for dimension agents."""
import importlib
import yaml
from pathlib import Path
from typing import Dict, Optional

_DIR = Path(__file__).parent
_registry = None


def get_registry() -> Dict[str, dict]:
    """Scan dimensions/ for subfolders with config.yaml, return {dim_key: {config, module_path, folder}}."""
    global _registry
    if _registry is not None:
        return _registry
    _registry = {}
    for entry in sorted(_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
            continue
        config_path = entry / "config.yaml"
        if not config_path.exists():
            continue
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        dim_key = config["dimension"]["key"]
        _registry[dim_key] = {
            "config": config,
            "module_path": f"dimensions.{entry.name}",
            "folder": entry,
        }
    return _registry


def get_prefix_map() -> Dict[str, str]:
    """Return sample_id prefix -> dimension key mapping. E.g. {"CD": "cd", "KS": "aging"}."""
    return {
        prefix.upper(): dim_key
        for dim_key, info in get_registry().items()
        for prefix in info["config"]["sample_id"]["prefixes"]
    }


def build_agent(dim_key: str, llm):
    """Dynamically import and build the agent for the given dimension."""
    reg = get_registry()
    if dim_key not in reg:
        raise KeyError(f"Unknown dimension: {dim_key}")
    mod = importlib.import_module(reg[dim_key]["module_path"])
    return mod.build_agent(llm)


def resolve_sample_id(sample_id: str) -> Optional[str]:
    """Determine dimension key from sample_id prefix. Tries longest prefix first."""
    pm = get_prefix_map()
    max_len = max((len(p) for p in pm), default=2)
    for length in range(max_len, 1, -1):
        if len(sample_id) >= length:
            prefix = sample_id[:length].upper()
            if prefix in pm:
                return pm[prefix]
    return None
