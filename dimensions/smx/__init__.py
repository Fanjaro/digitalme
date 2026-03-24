"""SMX 女性私密微生物 dimension agent."""
import yaml
from pathlib import Path
from langchain.agents import create_agent
from .tools import fetch_smx_data

_DIR = Path(__file__).parent

with open(_DIR / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)


def _load_prompt() -> str:
    with open(_DIR / "prompt.md", "r", encoding="utf-8") as f:
        return f.read()


def build_agent(llm):
    return create_agent(model=llm, tools=[fetch_smx_data], prompt=_load_prompt())
