import logging
import traceback
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field

from .config import DISCORD_WEBHOOK_URL

logger = logging.getLogger(__name__)

DISCORD_TIMEOUT = 15


class FeedbackRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    category: str = Field(..., min_length=1, max_length=50)
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=10, max_length=2000)


def send_feedback_notification(data: FeedbackRequest) -> bool:
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook not configured — set DISCORD_WEBHOOK_URL in Render environment")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    stars = "★" * data.rating + "☆" * (5 - data.rating)

    embed = {
        "title": "SafeHire AI — New Feedback",
        "description": f"Feedback submitted via the feedback form.",
        "color": 0x225BE3,
        "fields": [
            {"name": "Name", "value": data.name, "inline": True},
            {"name": "Email", "value": data.email, "inline": True},
            {"name": "Category", "value": data.category, "inline": True},
            {"name": "Rating", "value": f"{stars} ({data.rating}/5)", "inline": True},
            {"name": "Message", "value": data.message[:1024], "inline": False},
            {"name": "Submitted", "value": timestamp, "inline": False},
        ],
        "footer": {"text": "SafeHire AI — Build with Gemma Hackathon 2026"},
    }

    payload = {"embeds": [embed]}

    try:
        logger.info(f"Discord: posting feedback from {data.email} ...")
        resp = httpx.post(DISCORD_WEBHOOK_URL, json=payload, timeout=DISCORD_TIMEOUT)
        if resp.status_code in (200, 204):
            logger.info(f"Discord: feedback delivered (HTTP {resp.status_code})")
            return True
        else:
            logger.error(f"Discord webhook returned HTTP {resp.status_code}: {resp.text}")
            return False
    except httpx.TimeoutException:
        logger.error(f"Discord webhook timed out after {DISCORD_TIMEOUT}s\n{traceback.format_exc()}")
        return False
    except Exception as e:
        logger.error(f"Discord webhook failed: {e}\n{traceback.format_exc()}")
        return False
