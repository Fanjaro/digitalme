"""GM 过敏原IgE dimension agent."""
import yaml
from pathlib import Path
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from .tools import fetch_gm_data, analyze_gm_allergen_risks

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
    agent = create_tool_calling_agent(llm=llm, tools=[fetch_gm_data, analyze_gm_allergen_risks], prompt=prompt)
    return AgentExecutor(agent=agent, tools=[fetch_gm_data, analyze_gm_allergen_risks], handle_parsing_errors=True)
