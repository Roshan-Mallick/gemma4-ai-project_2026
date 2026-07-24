import json
import re
from .llm_client import call_gemma


def analyze_content(raw_text, entities):
    print(f"\n===== CONTENT ANALYSIS =====")
    print(f"  Text length: {len(raw_text)} chars")

    company = entities.get("company_name", "")
    email = entities.get("email", "")
    salary = entities.get("salary", "")
    phone = entities.get("phone", "")
    recruiter = entities.get("recruiter_name", "")
    job_title = entities.get("job_title", "")
    location = entities.get("location", "")
    website = entities.get("website", "")
    extra = entities.get("extra_info", "")

    prompt = f"""You are SafeHire AI, a cybersecurity analyst. Analyze the following job posting text for employment fraud indicators.

CRITICAL RULE: Every finding MUST cite the specific text that supports it. Do NOT infer or assume — only report what the text explicitly states.

JOB POSTING TEXT:
{raw_text[:3000]}

EXTRACTED INFO:
Company: {company}
Job Title: {job_title}
Salary: {salary}
Email: {email}
Phone: {phone}
Recruiter: {recruiter}
Location: {location}
Website: {website}
Extra: {extra}

Analyze these specific aspects. For each finding, cite the EXACT text or extracted field that supports it.

Reply with ONLY a JSON object (no markdown, no explanation):

{{
  "salary_realistic": true or false,
  "salary_explanation": "Cite the specific salary text and why it is realistic or unrealistic",
  "email_legitimate": true or false,
  "email_explanation": "Cite the specific email address and domain analysis",
  "grammar_quality": "good" or "fair" or "poor",
  "grammar_explanation": "Cite specific examples of grammar quality from the text",
  "urgency_pressure": true or false,
  "urgency_explanation": "Cite the exact urgency language found in the text",
  "payment_request": true or false,
  "payment_explanation": "Cite the exact payment request text, or state 'No payment request found in text'",
  "interview_too_easy": true or false,
  "interview_explanation": "Cite what the text says about the interview/hiring process",
  "contact_quality": "professional" or "suspicious" or "missing",
  "contact_explanation": "Cite the specific contact details and why they are professional/suspicious/missing",
  "company_known": true or false,
  "company_explanation": "Cite the company name and whether it matches a known legitimate company",
  "timeline_realistic": true or false,
  "timeline_explanation": "Cite any timeline/urgency text from the posting",
  "inconsistencies": ["list ONLY contradictions explicitly present in the text"],
  "red_flags": ["list ONLY red flag phrases/patterns explicitly found in the text — quote them"],
  "green_flags": ["list ONLY legitimacy indicators explicitly found in the text — quote them"],
  "content_risk_score": 0-100
}}

RULES:
- Every red_flag and green_flag must be a direct quote or close paraphrase from the text.
- Do NOT add generic scam warnings. Only cite what the text actually says.
- A salary of "$120,000/year for Software Engineer at Microsoft" is realistic.
- A salary of "$5000 per day for data entry" is NOT realistic.
- If the text contains NO payment requests, payment_request=false and red_flags must NOT include payment-related items.
- If the text contains NO urgency language, urgency_pressure=false and red_flags must NOT include urgency-related items.
- If company is well-known (Microsoft, Google, Amazon, etc.), mark company_known=true.
- content_risk_score: 0=definitely legitimate, 50=uncertain, 100=almost certainly a scam.
- You MUST return valid JSON. No extra text before or after the JSON object."""

    print(f"  [CONTENT] Calling Gemma for content analysis...")
    response = call_gemma(prompt, max_tokens=900)
    print(f"  [CONTENT] Gemma returned {len(response)} chars")
    print(f"  [CONTENT] Raw response:\n{response}")

    json_str = response
    start = response.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(response)):
            if response[i] == "{":
                depth += 1
            elif response[i] == "}":
                depth -= 1
                if depth == 0:
                    json_str = response[start:i+1]
                    break

    try:
        result = json.loads(json_str)
        print(f"  [CONTENT] Parsed successfully")
        print(f"  [CONTENT] content_risk_score: {result.get('content_risk_score', 'N/A')}")
        print(f"  [CONTENT] red_flags: {result.get('red_flags', [])}")
        print(f"  [CONTENT] green_flags: {result.get('green_flags', [])}")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  [CONTENT] JSON parse failed: {e}")
        result = {
            "salary_realistic": True,
            "salary_explanation": "Could not analyze",
            "email_legitimate": True,
            "email_explanation": "Could not analyze",
            "grammar_quality": "fair",
            "grammar_explanation": "Could not analyze",
            "urgency_pressure": False,
            "urgency_explanation": "Could not analyze",
            "payment_request": False,
            "payment_explanation": "Could not analyze",
            "interview_too_easy": False,
            "interview_explanation": "Could not analyze",
            "contact_quality": "missing",
            "contact_explanation": "Could not analyze",
            "company_known": False,
            "company_explanation": "Could not analyze",
            "timeline_realistic": True,
            "timeline_explanation": "Could not analyze",
            "inconsistencies": [],
            "red_flags": [],
            "green_flags": [],
            "content_risk_score": 50,
            "parse_error": str(e),
        }

    print(f"===== END CONTENT ANALYSIS =====\n")
    return result
