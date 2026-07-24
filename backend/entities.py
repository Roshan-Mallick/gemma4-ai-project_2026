import json
import re
from .llm_client import call_gemma

SCHEMA_KEYS = [
    "company_name", "recruiter_name", "email", "website", "phone",
    "salary", "location", "job_title", "skills", "extra_info",
]

FEWSHOT_INPUT = """Company: TechCorp Solutions
Job Title: Remote Content Writer
Salary: Rs.20000 to Rs.30000 per month
Contact: hr@techcorp.com
Phone: +91 98765 43210
Location: Work From Home
Requirement: Basic English writing skills"""

FEWSHOT_OUTPUT = """{
    "company_name": "TechCorp Solutions",
    "recruiter_name": "",
    "email": "hr@techcorp.com",
    "website": "",
    "phone": "+91 98765 43210",
    "salary": "Rs.20000 to Rs.30000 per month",
    "location": "Work From Home",
    "job_title": "Remote Content Writer",
    "skills": ["English writing"],
    "extra_info": ""
}"""


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON found in response: {text!r}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"No balanced JSON found in response: {text!r}")


def extract_entities(raw_text: str) -> dict:
    prompt = f"""Convert OCR text from job postings into JSON using this exact schema. Extract only what is literally present in the text; use "" or [] for anything missing.

IMPORTANT: Pay special attention to extracting:
- email addresses (even partial ones like "hr@company.com")
- website URLs (even partial like "www.company.com" or "company.com")
- company names
- phone numbers
- salary amounts

OCR TEXT:
{FEWSHOT_INPUT}

JSON:
{FEWSHOT_OUTPUT}

OCR TEXT:
{raw_text}

JSON:
"""
    print("\n===== ENTITY EXTRACTION =====")
    print(f"Prompt length: {len(prompt)} chars")
    print(f"OCR text length: {len(raw_text)} chars")

    response = call_gemma(prompt, max_tokens=768)
    print(f"----- RAW GEMMA RESPONSE (entity extraction) -----")
    print(response)
    print(f"----- END RAW RESPONSE -----")

    json_str = _extract_json_object(response)
    print(f"Parsed JSON string: {json_str[:500]}")

    try:
        entities = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"ERROR: Malformed JSON from model: {json_str!r}")
        raise ValueError(f"Malformed JSON from model: {json_str!r}")

    result = {k: entities.get(k, "" if k != "skills" else []) for k in SCHEMA_KEYS}

    print(f"----- EXTRACTED ENTITIES -----")
    for k, v in result.items():
        print(f"  {k}: {repr(v)}")
    print(f"----- END EXTRACTED ENTITIES -----")

    website = result.get("website", "")
    email = result.get("email", "")
    if not website and not email:
        print("WARNING: Both website AND email are empty. Attempting regex fallback...")

    raw_website, raw_email = _regex_extract_contact(raw_text)
    if not website and raw_website:
        result["website"] = raw_website
        website = raw_website
        print(f"  REGEX FALLBACK: website = {repr(raw_website)}")
    if not email and raw_email:
        result["email"] = raw_email
        email = raw_email
        print(f"  REGEX FALLBACK: email = {repr(raw_email)}")

    if not website and not email:
        print("WARNING: Both website AND email are empty. Investigation will have no domain to check.")

    return result


_URL_PATTERN = re.compile(
    r'(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?)',
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(
    r'\b([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b',
    re.IGNORECASE,
)


def _regex_extract_contact(text):
    if not text:
        return None, None

    found_website = None
    for m in _URL_PATTERN.finditer(text):
        url = m.group(1)
        if url and "." in url and len(url) > 4:
            skip_domains = {"example.com", "email.com", "domain.com", "test.com",
                            "company.com", "website.com", "job.com", "career.com",
                            "careers.google.com"}
            if url.lower().rstrip("/") not in skip_domains:
                found_website = url.rstrip("/")
                break

    found_email = None
    for m in _EMAIL_PATTERN.finditer(text):
        addr = m.group(1)
        if addr:
            found_email = addr
            break

    return found_website, found_email
