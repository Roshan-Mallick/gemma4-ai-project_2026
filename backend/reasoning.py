import json
import re
import urllib.request
from .llm_client import call_gemma


def quick_web_check(domain):
    if not domain:
        return {"reachable": False, "status_code": None}
    url = f"https://{domain}" if not domain.startswith("http") else domain
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return {"reachable": True, "status_code": response.getcode()}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def generate_reasoning_report(entities, investigation_results, content_analysis=None):
    target_domain = (
        investigation_results.get("Company", {}).get("Website Domain")
        or investigation_results.get("Email", {}).get("Domain")
    )
    print(f"  [REASONING] target_domain={repr(target_domain)}")
    web_status = quick_web_check(target_domain) if target_domain else {"reachable": False}
    investigation_results["Live_Web_Verification"] = web_status
    print(f"  [REASONING] live web check: {web_status}")

    summary = investigation_results.get("_summary", {})
    unknown_count = summary.get("unknown_count", 0)
    pass_count = summary.get("pass_count", 0)
    fail_count = summary.get("fail_count", 0)

    domain_res = investigation_results.get("Domain", {})
    dns_res = investigation_results.get("DNS", {})
    ssl_res = investigation_results.get("SSL", {})
    email_res = investigation_results.get("Email", {})
    http_res = investigation_results.get("HTTP Headers", {})
    company_res = investigation_results.get("Company", {})

    evidence_summary = f"""TECHNICAL EVIDENCE INVENTORY:
Domain: status={domain_res.get('status','UNKNOWN')}, registered={domain_res.get('Registered')}, creation_date={domain_res.get('Creation Date','N/A')}, domain_age={domain_res.get('Domain Age','N/A')}
DNS: status={dns_res.get('status','UNKNOWN')}, A={dns_res.get('A Record',[])}, MX={dns_res.get('MX Record',[])}, SPF={dns_res.get('SPF',False)}, DMARC={dns_res.get('DMARC',False)}
SSL: status={ssl_res.get('status','UNKNOWN')}, https={ssl_res.get('HTTPS Available',False)}, cert_valid={ssl_res.get('Certificate Valid',False)}, issuer={ssl_res.get('Issuer','N/A')}
Email: status={email_res.get('status','UNKNOWN')}, free={email_res.get('Free Provider',False)}, disposable={email_res.get('Disposable Provider',False)}, typosquat={email_res.get('Typosquatting',False)}, risk_score={email_res.get('Risk Score','N/A')}
HTTP: status={http_res.get('status','UNKNOWN')}, status_code={http_res.get('status_code','N/A')}, server={http_res.get('server','N/A')}
Company: domain_match={company_res.get('Email Domain Match',False)}, website_domain={company_res.get('Website Domain','N/A')}
Live Web: reachable={web_status.get('reachable',False)}

EXTRACTED ENTITIES FROM OCR:
{json.dumps(entities, indent=2)}

ORIGINAL OCR TEXT (first 2000 chars):
(See content analysis below for parsed findings)

CONTENT ANALYSIS FINDINGS:
{json.dumps(content_analysis, indent=2) if content_analysis else 'No content analysis available'}

TECHNICAL CHECK SUMMARY: {pass_count} PASSED, {fail_count} FAILED, {unknown_count} UNKNOWN"""

    prompt = f"""You are SafeHire AI, a cybersecurity analyst specializing in employment fraud detection.

Your job is to analyze evidence and produce an auditable risk assessment. You are NOT a detective making accusations — you are an analyst reporting what the evidence confirms.

{evidence_summary}

═══════════════════════════════════════════════════════════
STRICT RULES — VIOLATION = WRONG ANSWER:
═══════════════════════════════════════════════════════════

1. EVERY RED FLAG MUST HAVE EVIDENCE.
   Format: "- [Flag Name]: [Evidence from the data above]. Source: [technical/ocr/content]"
   If you cannot cite specific evidence, DO NOT list it as a red flag.

2. NEVER INFER MISSING INFORMATION.
   BAD:  "Interview process was bypassed" (unless OCR text explicitly says "no interview" or "start immediately")
   BAD:  "No official recruiter" (unless entity extraction returned empty recruiter AND no email signature)
   BAD:  "Fake company" (unless technical investigation shows domain is parked/malicious)
   GOOD: "Email domain 'scam.xyz' has no MX records (DNS investigation: MX Record=[])" 
   GOOD: "OCR text contains 'Send $50 registration fee via Western Union' (content analysis: payment_request=true)"

3. UNKNOWN MEANS UNKNOWN — NOT SUSPICIOUS.
   status=UNKNOWN means the check could not run (e.g., no domain available).
   NEVER count UNKNOWN results as evidence of fraud.
   If most checks are UNKNOWN, state "Insufficient technical evidence to assess domain legitimacy."

4. SEPARATE CONFIRMED FACTS FROM SPECULATION.
   Confirmed: "SSL certificate expires 2026-10-15, issued by Let's Encrypt" (from ssl investigation)
   Speculation: "This is a fly-by-night operation" (DO NOT SAY THIS unless you have WHOIS evidence)

5. DO NOT APPLY GENERIC SCAM PATTERNS UNLESS PRESENT IN EVIDENCE.
   BAD:  "Common scam pattern: advance fee" (unless payment_request=true in content analysis)
   BAD:  "Classic phishing email" (unless email has suspicious domain AND content shows phishing language)
   GOOD: "Payment request detected in OCR text: '$50 registration fee' (content analysis)"

6. SCORE HONESTLY — DO NOT INFLATE.
   If technical checks are mostly PASS with valid SSL/DNS/WHOIS, the score MUST be low (0-25) regardless of content analysis.
   Content analysis alone should not push score above 70 unless it contains payment requests or clear fraud evidence.

═══════════════════════════════════════════════════════════
OUTPUT FORMAT (follow exactly):
═══════════════════════════════════════════════════════════

**Risk Score:** [0-100 integer]
**Final Verdict:** [SAFE / CAUTION / LIKELY SCAM]

**RED FLAGS:**
* [Flag]: [Evidence]. Source: [technical/ocr/content]
* [Flag]: [Evidence]. Source: [technical/ocr/content]
(Or "None detected" if no evidence supports any red flags)

**GREEN FLAGS:**
* [Flag]: [Evidence]. Source: [technical/ocr/content]
* [Flag]: [Evidence]. Source: [technical/ocr/content]

**EVIDENCE SUMMARY:**
* Technical checks passed: {pass_count}
* Technical checks failed: {fail_count}  
* Technical checks unknown (could not run): {unknown_count}
* Content analysis red flags: {len(content_analysis.get('red_flags', [])) if content_analysis else 'N/A'}
* Content analysis green flags: {len(content_analysis.get('green_flags', [])) if content_analysis else 'N/A'}

**VERDICT REASONING:**
[3-5 sentences. Reference SPECIFIC evidence. State what is confirmed vs what is uncertain. Conclude based on evidence weight.]"""

    print(f"  [REASONING] Calling Gemma with {len(prompt)} char prompt...")
    result = call_gemma(prompt, max_tokens=600)
    print(f"  [REASONING] Gemma returned {len(result)} chars")
    return result


def parse_reasoning(report_text):
    result = {"risk_score": 50, "verdict": "CAUTION", "red_flags": [], "green_flags": [], "explanation": ""}

    score_match = re.search(r"\*\*Risk Score:\*\*\s*(\d+)", report_text)
    if score_match:
        result["risk_score"] = int(score_match.group(1))

    verdict_match = re.search(r"\*\*Final Verdict:\*\*\s*(SAFE|CAUTION|LIKELY SCAM)", report_text, re.IGNORECASE)
    if verdict_match:
        result["verdict"] = verdict_match.group(1).upper()

    red_match = re.search(r"\*\*RED FLAGS:\*\*\s*\n(.*?)(?=\*\*GREEN|$)", report_text, re.DOTALL)
    if red_match:
        flags = re.findall(r"\*\s*(.+)", red_match.group(1))
        result["red_flags"] = [f.strip() for f in flags if f.strip().lower() != "none detected"]

    green_match = re.search(r"\*\*GREEN FLAGS:\*\*\s*\n(.*?)(?=\*\*EVIDENCE|$)", report_text, re.DOTALL)
    if not green_match:
        green_match = re.search(r"\*\*GREEN FLAGS:\*\*\s*\n(.*?)(?=\*\*VERDICT|$)", report_text, re.DOTALL)
    if green_match:
        flags = re.findall(r"\*\s*(.+)", green_match.group(1))
        result["green_flags"] = [f.strip() for f in flags if f.strip().lower() != "none detected"]

    reason_match = re.search(r"\*\*VERDICT REASONING:\*\*\s*\n(.+)", report_text, re.DOTALL)
    if reason_match:
        result["explanation"] = reason_match.group(1).strip()

    return result
