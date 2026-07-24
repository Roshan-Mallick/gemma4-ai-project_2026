import time
import logging
from openai import OpenAI
from .config import OPENROUTER_API_KEY, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

LM_STUDIO_URL = "http://localhost:1234/v1"

_cloud_client = None
if OPENROUTER_API_KEY:
    _cloud_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

_local_client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")

_lm_studio_healthy = None
_lm_studio_check_time = 0
CHECK_INTERVAL = 60
MAX_RETRIES = 3
RETRY_DELAY = 2


def _check_lm_studio() -> bool:
    global _lm_studio_healthy, _lm_studio_check_time
    now = time.time()
    if _lm_studio_healthy is not None and (now - _lm_studio_check_time) < CHECK_INTERVAL:
        return _lm_studio_healthy
    try:
        resp = _local_client.models.list()
        _lm_studio_healthy = len(resp.data) > 0
    except Exception:
        _lm_studio_healthy = False
    _lm_studio_check_time = now
    logger.info("LM Studio health: %s", _lm_studio_healthy)
    return _lm_studio_healthy


def call_gemma(prompt: str, max_tokens: int = 768, temperature: float = 0.0) -> str:
    if _cloud_client:
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
                    logger.warning("OpenRouter all %d attempts failed, trying LM Studio: %s", MAX_RETRIES, e)

    if _check_lm_studio():
        print(f"  [LLM] Calling LM Studio (localhost:1234)...")
        try:
            resp = _local_client.chat.completions.create(
                model="gemma",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = resp.choices[0].message.content
            if content is None:
                raise ValueError("LM Studio returned empty content")
            content = content.strip()
            print(f"  [LLM] LM Studio response: {len(content)} chars")
            return content
        except Exception as e:
            print(f"  [LLM] LM Studio FAILED: {type(e).__name__}: {e}")
            logger.warning("LM Studio call also failed: %s", e)

    print("  [LLM] ERROR: No LLM available")
    raise RuntimeError("No LLM available: OpenRouter failed and LM Studio offline")


def get_llm_status() -> dict:
    return {
        "openrouter": _cloud_client is not None,
        "lm_studio": _check_lm_studio() if _cloud_client is None else "skipped (openrouter active)",
        "active": "openrouter" if _cloud_client else ("lm_studio" if _check_lm_studio() else "none"),
    }
