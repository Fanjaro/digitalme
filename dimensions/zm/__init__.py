"""ZM 自身免疫抗体 dimension agent."""
import yaml
from pathlib import Path
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from .tools import fetch_zm_data

_DIR = Path(__file__).parent

with open(_DIR / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)


def _load_prompt() -> str:
    with open(_DIR / "prompt.md", "r", encoding="utf-8") as f:
        return f.read()


def build_agent(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", _load_prompt()),
        ("placeholder", "{messages}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    return create_react_agent(llm=llm, tools=[fetch_zm_data], prompt=prompt)
