# llm_config_list.py
# Loads LLM configurations from environment variables
# This replaces the old llm_config_list.json approach
# Usage: from llm_config_list import config_list

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def _get_model_config(model: str, api_key: str, base_url: str, tags: list[str]) -> dict:
    """Build a model config dict, skipping if api_key is not set."""
    if not api_key or api_key == "your-api-key":
        return None
    return {
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "tags": tags,
    }


config_list = [
    # GPT-4 series
    _get_model_config(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        tags=["gpt-4o", "tool"],
    ),
    # DeepSeek via Pro endpoint
    _get_model_config(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3"),
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://pro.deepseek.com"),
        tags=["deepseek-v3", "tool"],
    ),
    # DeepSeek R1 (reasoning model)
    _get_model_config(
        model=os.getenv("DEEPSEEK_R1_MODEL", "deepseek-ai/DeepSeek-R1"),
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://pro.deepseek.com"),
        tags=["deepseek-r1", "reasoning"],
    ),
    # Custom LLM endpoint (for local models, LM Studio, etc.)
    _get_model_config(
        model=os.getenv("CUSTOM_LLM_MODEL", ""),
        api_key=os.getenv("CUSTOM_LLM_API_KEY", ""),
        base_url=os.getenv("CUSTOM_LLM_BASE_URL", ""),
        tags=["custom", "tool"],
    ),
]

# Filter out None entries (configs without valid API keys)
config_list = [cfg for cfg in config_list if cfg is not None]


if __name__ == "__main__":
    print(f"Loaded {len(config_list)} LLM configuration(s):")
    for cfg in config_list:
        print(f"  - {cfg['model']} ({cfg['base_url']})")
