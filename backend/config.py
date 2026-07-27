import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass


def _require(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        print(f"[CONFIG] WARNING: {key} not set in .env")
    return val


OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

ABSTRACT_EMAIL_API_KEY = os.getenv("ABSTRACT_EMAIL_API_KEY", "")
ABSTRACT_EMAIL_API_URL = os.getenv("ABSTRACT_EMAIL_API_URL", "https://emailvalidation.abstractapi.com/v1/")
ABSTRACT_PHONE_API_KEY = os.getenv("ABSTRACT_PHONE_API_KEY", "")
ABSTRACT_PHONE_API_URL = os.getenv("ABSTRACT_PHONE_API_URL", "https://phoneintelligence.abstractapi.com/v1/")
ABSTRACT_IP_API_KEY = os.getenv("ABSTRACT_IP_API_KEY", "")
ABSTRACT_IP_API_URL = os.getenv("ABSTRACT_IP_API_URL", "https://ipgeolocation.abstractapi.com/v1/")

DNS_OVER_HTTPS_PRIMARY = os.getenv("DNS_OVER_HTTPS_PRIMARY", "https://dns.google/resolve")
DNS_OVER_HTTPS_FALLBACK = os.getenv("DNS_OVER_HTTPS_FALLBACK", "https://cloudflare-dns.com/dns-query")

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "icloud.com", "proton.me", "protonmail.com", "aol.com", "zoho.com",
}

DISPOSABLE_EMAIL_PROVIDERS = {
    "mailinator.com", "10minutemail.com", "tempmail.com",
    "guerrillamail.com", "yopmail.com", "sharklasers.com",
}

FEEDBACK_EMAIL = os.getenv("EMAIL", "")
FEEDBACK_EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
FEEDBACK_RECIPIENTS = [
    "roshanmallick2025@gmail.com",
    "aditya2006mishra123@gmail.com",
    "omsrivastava6126@gmail.com",
]
