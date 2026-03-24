"""Global configuration for DigitalMe multi-agent system."""

import os
import logging
import threading

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── 内部 API ───
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE_URL", "http://10.1.20.128:30080")
API_V1_SAMPLES = f"{INTERNAL_API_BASE}/api/v1/samples/"
API_V2_SAMPLES = f"{INTERNAL_API_BASE}/api/v2/samples/"
API_V1_USERS = f"{INTERNAL_API_BASE}/api/v1/users/by-sample/"

# ─── Anthropic (主力模型) ───
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# ─── 豆包 (保底模型) ───
# 豆包使用 OpenAI 兼容接口，需要配置以下环境变量：
#   DOUBAO_API_KEY       - 火山引擎 API Key
#   DOUBAO_BASE_URL      - 豆包 API 地址（火山引擎推理接入点）
#   DOUBAO_MODEL         - 模型 endpoint id（在火山引擎控制台创建的推理接入点 ID）
DOUBAO_API_KEY = os.getenv("DOUBAO_API_KEY", "")
DOUBAO_BASE_URL = os.getenv(
    "DOUBAO_BASE_URL",
    "https://ark.cn-beijing.volces.com/api/v3",  # 火山引擎 ARK 默认地址
)
DOUBAO_MODEL = os.getenv(
    "DOUBAO_MODEL",
    "ep-m-20260308162656-cmtcr",  # 替换为你的推理接入点 ID
)

_llm = None
_llm_lock = threading.Lock()


def _create_anthropic_llm():
    """尝试创建 Anthropic Claude 实例。"""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model=ANTHROPIC_MODEL, temperature=0)
    # 发送一个轻量级请求验证连通性
    llm.invoke("ping")
    logger.info("✅ Anthropic Claude 初始化成功，使用模型: %s", ANTHROPIC_MODEL)
    return llm


def _create_doubao_llm():
    """
    创建豆包模型实例（保底）。
    豆包基于火山引擎 ARK，提供 OpenAI 兼容接口，
    直接用 langchain_openai.ChatOpenAI 接入。
    """
    from langchain_openai import ChatOpenAI

    if not DOUBAO_API_KEY:
        raise ValueError(
            "DOUBAO_API_KEY 未配置，无法初始化豆包模型。"
            "请在 .env 中设置 DOUBAO_API_KEY。"
        )

    llm = ChatOpenAI(
        model=DOUBAO_MODEL,
        openai_api_key=DOUBAO_API_KEY,
        openai_api_base=DOUBAO_BASE_URL,
        temperature=0,
        # 豆包特定参数可通过 model_kwargs 传入
        model_kwargs={},
    )
    logger.info("✅ 豆包模型初始化成功，使用接入点: %s", DOUBAO_MODEL)
    return llm


def get_llm():
    """
    获取 LLM 实例。
    优先级: Anthropic Claude → 豆包 Doubao
    一旦初始化成功会缓存，后续直接复用。
    """
    global _llm
    with _llm_lock:
        if _llm is not None:
            return _llm

        # --- 第一优先级：Anthropic Claude ---
        try:
            _llm = _create_anthropic_llm()
            return _llm
        except Exception as e:
            logger.warning(
                "⚠️ Anthropic Claude 初始化失败: %s，尝试降级到豆包模型...", e
            )

        # --- 第二优先级：豆包 Doubao (保底) ---
        try:
            _llm = _create_doubao_llm()
            return _llm
        except Exception as e:
            logger.error("❌ 豆包模型初始化也失败: %s", e)
            raise RuntimeError(
                f"所有 LLM 均初始化失败。"
                f"Anthropic 和豆包模型均不可用，请检查 API Key 和网络配置。"
            ) from e