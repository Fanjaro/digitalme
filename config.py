"""Global configuration for DigitalMe multi-agent system."""
import os
import threading
from dotenv import load_dotenv

load_dotenv()

INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE_URL", "http://10.1.20.128:30080")
API_V1_SAMPLES = f"{INTERNAL_API_BASE}/api/v1/samples/"
API_V2_SAMPLES = f"{INTERNAL_API_BASE}/api/v2/samples/"
API_V1_USERS = f"{INTERNAL_API_BASE}/api/v1/users/by-sample/"

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

_llm = None
_llm_lock = threading.Lock()

def get_llm():
    global _llm
    with _llm_lock:
        if _llm is None:
            from langchain_anthropic import ChatAnthropic
            _llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0)
        return _llm
