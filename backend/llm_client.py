import time
import logging
from openai import OpenAI
from .config import (
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL,
)

logger = logging.getLogger(__name__)

_cloud_client = None
if OPENROUTER_API_KEY:
    _cloud_client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )

MAX_RETRIES = 3
RETRY_DELAY = 2


def call_gemma(prompt: str, max_tokens: int = 768, temperature: float = 0.0) -> str:
    if not _cloud_client:
        raise RuntimeError("OpenRouter API key not configured")

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  [LLM] Calling OpenRouter ({OPENROUTER_MODEL}) attempt {attempt}/{MAX_RETRIES}...")
        try:
            resp = _cloud_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.choices[0].message.content
            if content is None:
                raise ValueError("OpenRouter returned empty content")
            content = content.strip()
            if not content:
                raise ValueError("OpenRouter returned empty string")
            print(f"  [LLM] OpenRouter response: {len(content)} chars")
            return content
        except Exception as e:
            print(f"  [LLM] OpenRouter attempt {attempt} FAILED: {type(e).__name__}: {e}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * attempt
                print(f"  [LLM] Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error("OpenRouter all %d attempts failed: %s", MAX_RETRIES, e)
                raise


def get_llm_status() -> dict:
    return {
        "openrouter": _cloud_client is not None,
        "active": "openrouter" if _cloud_client else "none",
    }
