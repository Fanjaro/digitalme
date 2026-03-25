"""GM 过敏原IgE dimension agent."""
import yaml
from pathlib import Path
from langgraph.prebuilt import create_react_agent
from .tools import fetch_gm_data, analyze_gm_allergen_risks

_DIR = Path(__file__).parent

with open(_DIR / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)


def _load_prompt() -> str:
    with open(_DIR / "prompt.md", "r", encoding="utf-8") as f:
        return f.read()


def build_agent(llm):
    return create_react_agent(model=llm, tools=[fetch_gm_data, analyze_gm_allergen_risks], prompt=_load_prompt())
