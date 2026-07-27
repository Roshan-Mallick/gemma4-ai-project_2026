import json
import socket
import logging
import asyncio
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .config import CORS_ORIGINS
from .ocr import extract_text_from_image
from .entities import extract_entities
from .investigation import run_investigation, extract_domain
from .analysis import analyze_content
from .reasoning import generate_reasoning_report, parse_reasoning
from .llm_client import get_llm_status
from .feedback import FeedbackRequest, send_feedback_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SafeHire AI", version="1.0.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"\n{'='*60}")
    print(f"UNHANDLED EXCEPTION on {request.method} {request.url.path}")
    print(f"Type: {type(exc).__name__}")
    print(f"Message: {exc}")
    traceback.print_exc()
    print(f"{'='*60}\n")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server error: {type(exc).__name__}: {str(exc)}"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _status_val(investigation_section, field, default="UNKNOWN"):
    status = investigation_section.get("status", default)
    return status


def _build_technical_checks(investigation, entities):
    email_res = investigation.get("Email", {})
    domain_res = investigation.get("Domain", {})
    dns_res = investigation.get("DNS", {})
    ssl_res = investigation.get("SSL", {})
    company = investigation.get("Company", {})
    http_res = investigation.get("HTTP Headers", {})

    def domain_status():
        if domain_res.get("status") == "PASS" and domain_res.get("Registered") is True:
            return "PASS"
        elif domain_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        else:
            return "FAIL"

    def https_status():
        if ssl_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if ssl_res.get("HTTPS Available") else "FAIL"

    def ssl_status():
        if ssl_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if ssl_res.get("Certificate Valid") else "FAIL"

    def mx_status():
        if dns_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if len(dns_res.get("MX Record", [])) > 0 else "FAIL"

    def spf_status():
        if dns_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if dns_res.get("SPF") else "FAIL"

    def dmarc_status():
        if dns_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if dns_res.get("DMARC") else "FAIL"

    def http_status():
        if http_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        code = http_res.get("status_code")
        return "PASS" if code == 200 else "FAIL"

    def email_domain_status():
        if email_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if company.get("Email Domain Match", False) else "FAIL"

    def disposable_email_status():
        if email_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "FAIL" if email_res.get("Disposable Provider", False) else "PASS"

    def free_email_status():
        if email_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "FAIL" if email_res.get("Free Provider", False) else "PASS"

    def robots_status():
        if robots.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if robots.get("found", False) else "UNKNOWN"

    def sitemap_status():
        if sitemap.get("status") == "UNKNOWN":
            return "UNKNOWN"
        return "PASS" if sitemap.get("found", False) else "UNKNOWN"

    def live_status():
        web_check = investigation.get("Live_Web_Verification", {})
        if not company.get("Website Domain"):
            return "UNKNOWN"
        if web_check.get("reachable", False):
            return "PASS"
        http_code = http_res.get("status_code")
        if http_code and http_code > 0:
            return "PASS"
        return "FAIL"

    phone_res = investigation.get("Phone", {})

    def phone_valid_status():
        if phone_res.get("status") == "UNKNOWN":
            return "UNKNOWN"
        if phone_res.get("is_valid") is False:
            return "FAIL"
        return "PASS"

    return {
        "domain_registered": domain_status(),
        "website_reachable": live_status(),
        "https_enabled": https_status(),
        "ssl_valid": ssl_status(),
        "mx_record": mx_status(),
        "spf_record": spf_status(),
        "dmarc_record": dmarc_status(),
        "email_domain_match": email_domain_status(),
        "disposable_email": disposable_email_status(),
        "free_email": free_email_status(),
        "live_verification": live_status(),
        "phone_valid": phone_valid_status(),
    }


def _build_risk_indicators(technical, investigation):
    salary_res = investigation.get("Salary", {})
    domain_res = investigation.get("Domain", {})
    summary = investigation.get("_summary", {})

    def label_for(status):
        if status == "PASS":
            return "Pass"
        elif status == "FAIL":
            return "Fail"
        elif status == "UNKNOWN":
            return "Unknown"
        return "N/A"

    return {
        "domain_registered": label_for(technical["domain_registered"]),
        "https_enabled": label_for(technical["https_enabled"]),
        "ssl_valid": label_for(technical["ssl_valid"]),
        "mx_record": label_for(technical["mx_record"]),
        "spf_record": label_for(technical["spf_record"]),
        "dmarc_record": label_for(technical["dmarc_record"]),
        "email_domain_match": label_for(technical["email_domain_match"]),
        "phone_valid": label_for(technical.get("phone_valid", "UNKNOWN")),
        "suspicious_salary": "Yes" if salary_res.get("Suspicious Salary") else "No",
        "domain_age": domain_res.get("Creation Date", "Unknown") or "Unknown",
        "domain_source": summary.get("domain_source", "unknown"),
        "checks_pass": summary.get("pass_count", 0),
        "checks_fail": summary.get("fail_count", 0),
        "checks_unknown": summary.get("unknown_count", 0),
    }


def _build_technical_evidence(investigation):
    dns_res = investigation.get("DNS", {})
    ssl_res = investigation.get("SSL", {})
    domain_res = investigation.get("Domain", {})
    robots = investigation.get("Robots.txt", {})
    sitemap = investigation.get("Sitemap", {})
    http = investigation.get("HTTP Headers", {})
    email_res = investigation.get("Email", {})
    phone_res = investigation.get("Phone", {})

    return {
        "whois": {
            "status": domain_res.get("status", "UNKNOWN"),
            "created": domain_res.get("Creation Date"),
            "expires": domain_res.get("Expiry Date"),
            "registrar": domain_res.get("Registrar"),
            "registered": domain_res.get("Registered"),
        },
        "dns": {
            "status": dns_res.get("status", "UNKNOWN"),
            "a": dns_res.get("A Record", []),
            "aaaa": dns_res.get("AAAA Record", []),
            "mx": dns_res.get("MX Record", []),
            "ns": dns_res.get("NS Record", []),
            "txt": dns_res.get("TXT Record", []),
            "spf": dns_res.get("SPF", False),
            "dmarc": dns_res.get("DMARC", False),
        },
        "tls": {
            "status": ssl_res.get("status", "UNKNOWN"),
            "version": ssl_res.get("TLS Version"),
            "issuer": ssl_res.get("Issuer"),
            "https_available": ssl_res.get("HTTPS Available", False),
            "certificate_valid": ssl_res.get("Certificate Valid", False),
            "valid_from": ssl_res.get("Valid From"),
            "valid_until": ssl_res.get("Valid Until"),
            "days_remaining": ssl_res.get("Days Remaining"),
        },
        "http_status": http.get("status_code"),
        "robots_txt": robots,
        "sitemap": sitemap,
        "http_headers": http,
        "email_validation": {
            "status": email_res.get("status", "UNKNOWN"),
            "deliverability": email_res.get("abstract_api", {}).get("deliverability") if email_res.get("abstract_api") else None,
            "quality_score": email_res.get("abstract_api", {}).get("quality_score") if email_res.get("abstract_api") else None,
            "is_free_email": email_res.get("abstract_api", {}).get("is_free_email") if email_res.get("abstract_api") else None,
            "is_disposable": email_res.get("abstract_api", {}).get("is_disposable_email") if email_res.get("abstract_api") else None,
            "is_role_email": email_res.get("abstract_api", {}).get("is_role_email") if email_res.get("abstract_api") else None,
            "is_catchall": email_res.get("abstract_api", {}).get("is_catchall_email") if email_res.get("abstract_api") else None,
            "is_mx_found": email_res.get("abstract_api", {}).get("is_mx_found") if email_res.get("abstract_api") else None,
            "is_smtp_valid": email_res.get("abstract_api", {}).get("is_smtp_valid") if email_res.get("abstract_api") else None,
            "autocorrect": email_res.get("abstract_api", {}).get("autocorrect") if email_res.get("abstract_api") else "",
            "risk_score": email_res.get("Risk Score", 0),
        },
        "phone_intelligence": {
            "status": phone_res.get("status", "UNKNOWN"),
            "is_valid": phone_res.get("is_valid"),
            "line_type": phone_res.get("line_type"),
            "line_status": phone_res.get("line_status"),
            "carrier": phone_res.get("carrier_name"),
            "country": phone_res.get("country"),
            "country_code": phone_res.get("country_code"),
            "region": phone_res.get("region"),
            "city": phone_res.get("city"),
            "risk_level": phone_res.get("risk_level"),
            "total_breaches": phone_res.get("total_breaches", 0),
            "risk_score": phone_res.get("Risk Score", 0),
        },
    }


def _compute_technical_risk(investigation):
    summary = investigation.get("_summary", {})
    pass_count = summary.get("pass_count", 0)
    fail_count = summary.get("fail_count", 0)
    unknown_count = summary.get("unknown_count", 0)
    total = pass_count + fail_count + unknown_count

    if total == 0:
        return 50

    fail_ratio = fail_count / total
    pass_ratio = pass_count / total

    if fail_ratio >= 0.5:
        risk = 70 + int(fail_ratio * 30)
    elif fail_ratio >= 0.3:
        risk = 40 + int(fail_ratio * 40)
    elif fail_count == 0 and pass_count > 0:
        risk = max(0, 15 - pass_count * 3)
    elif fail_count > 0:
        risk = 20 + int(fail_ratio * 50)
    else:
        risk = 30 + int(unknown_count * 3)

    return max(0, min(100, risk))


def _compute_verdict_and_confidence(risk_score, ai_reasoning, investigation_summary):
    verdict = ai_reasoning.get("verdict", "CAUTION").upper()
    unknown_count = investigation_summary.get("unknown_count", 0)
    total_checks = unknown_count + investigation_summary.get("pass_count", 0) + investigation_summary.get("fail_count", 0)

    if total_checks > 0 and unknown_count == total_checks:
        if verdict == "LIKELY SCAM":
            verdict = "CAUTION"
            ai_reasoning["explanation"] = (
                "All technical checks returned Unknown because no verified domain was available. "
                "This does not constitute evidence of fraud. " + (ai_reasoning.get("explanation", "") or "")
            )

    if risk_score <= 25:
        confidence = "High" if risk_score <= 15 else "Medium"
    elif risk_score <= 60:
        confidence = "Medium"
    else:
        confidence = "High" if risk_score >= 75 else "Medium"
    return verdict, confidence


@app.post("/api/analyze")
async def analyze(
    image: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
):
    print(f"\n{'='*60}")
    print(f"=== ANALYZE REQUEST ===")
    print(f"image: {image}")
    print(f"image.filename: {image.filename if image else None}")
    print(f"image.content_type: {image.content_type if image else None}")
    print(f"text: {repr(text[:100]) if text else None}")

    try:
        if image:
            file_bytes = await image.read()
            print(f"\nSTEP 1 - OCR")
            print(f"Read {len(file_bytes)} bytes from {image.filename}")
            raw_text = extract_text_from_image(file_bytes)
            print(f"OCR extracted {len(raw_text)} chars")
            print(f"----- OCR TEXT -----")
            print(raw_text[:3000])
            print(f"----- END OCR TEXT -----")
            source_type = "image"
            source_filename = image.filename
        elif text:
            print(f"\nSTEP 1 - TEXT INPUT")
            print(f"Received text input: {len(text)} chars")
            raw_text = text
            source_type = "text"
            source_filename = None
        else:
            print("400 Reason: No image and no text provided")
            return JSONResponse(status_code=400, content={"detail": "Provide an image file or text input"})

        if not raw_text:
            print("422 Reason: OCR returned empty text")
            return JSONResponse(status_code=422, content={"detail": "No text could be extracted from the input"})

        print(f"\nSTEP 2 - ENTITY EXTRACTION (calling Gemma)...")
        entities = extract_entities(raw_text)

        website = entities.get("website", "")
        email = entities.get("email", "")
        company = entities.get("company_name", "")
        print(f"\nSTEP 3 - ENTITY SUMMARY")
        print(f"  company_name = {repr(company)}")
        print(f"  website      = {repr(website)}")
        print(f"  email        = {repr(email)}")
        if not website and not email:
            print(f"  >>> No website or email extracted. Investigation will derive domain from company name.")

        print(f"\nSTEP 4 - TECHNICAL INVESTIGATION")
        investigation = run_investigation(entities)

        print(f"\nSTEP 5 - CONTENT ANALYSIS (calling Gemma)...")
        content_analysis = analyze_content(raw_text, entities)

        print(f"\nSTEP 6 - AI REASONING (calling Gemma)...")
        raw_reasoning = generate_reasoning_report(entities, investigation, content_analysis)
        print(f"----- RAW REASONING -----")
        print(raw_reasoning)
        print(f"----- END RAW REASONING -----")
        ai_reasoning_parsed = parse_reasoning(raw_reasoning)
        print(f"----- PARSED REASONING -----")
        print(json.dumps(ai_reasoning_parsed, indent=2))
        print(f"----- END PARSED REASONING -----")

        technical = _build_technical_checks(investigation, entities)
        risk_indicators = _build_risk_indicators(technical, investigation)
        technical_evidence = _build_technical_evidence(investigation)

        technical_risk = _compute_technical_risk(investigation)
        content_risk = content_analysis.get("content_risk_score", 50)
        reasoning_risk = ai_reasoning_parsed.get("risk_score", 50)
        combined_risk = round((technical_risk * 0.35) + (content_risk * 0.30) + (reasoning_risk * 0.35))
        combined_risk = max(0, min(100, combined_risk))
        print(f"\n  Risk scores: technical={technical_risk}, content={content_risk}, reasoning={reasoning_risk}, combined={combined_risk}")

        investigation_summary = investigation.get("_summary", {})
        verdict, confidence = _compute_verdict_and_confidence(combined_risk, ai_reasoning_parsed, investigation_summary)

        print(f"\n  Risk adjustment: unknown_count={investigation_summary.get('unknown_count', 0)}, pass={investigation_summary.get('pass_count', 0)}, fail={investigation_summary.get('fail_count', 0)}")

        job_info = {
            "company": entities.get("company_name", ""),
            "title": entities.get("job_title", ""),
            "location": entities.get("location", ""),
            "salary": entities.get("salary", ""),
            "recruiter": entities.get("recruiter_name", ""),
            "email": entities.get("email", ""),
            "phone": entities.get("phone", ""),
            "website": entities.get("website", ""),
            "skills": ", ".join(entities.get("skills", [])) if isinstance(entities.get("skills"), list) else str(entities.get("skills", "")),
        }

        report_id = "local-" + str(id(job_info))

        response = {
            "verdict": verdict,
            "risk_score": combined_risk,
            "risk_breakdown": {
                "technical_risk": technical_risk,
                "content_risk": content_risk,
                "reasoning_risk": reasoning_risk,
            },
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report_id": report_id,
            "job_info": job_info,
            "ai_reasoning": ai_reasoning_parsed,
            "technical": technical,
            "risk_indicators": risk_indicators,
            "technical_evidence": technical_evidence,
            "content_analysis": content_analysis,
        }
        print(f"\nSTEP 7 - FINAL RESULT")
        print(f"  verdict={verdict} score={combined_risk} confidence={confidence}")
        print(f"  technical_risk={technical_risk} content_risk={content_risk} reasoning_risk={reasoning_risk}")
        print(f"  domain_investigated={investigation.get('Company', {}).get('Website Domain')}")
        print(f"{'='*60}\n")
        return response

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"EXCEPTION in analyze(): {type(e).__name__}: {e}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        return JSONResponse(
            status_code=500,
            content={"detail": f"{type(e).__name__}: {str(e)}"},
        )


# ---------------------------------------------------------------------------
# SSE STREAMING ENDPOINT
# ---------------------------------------------------------------------------
@app.post("/api/analyze-stream")
async def analyze_stream(
    image: Optional[UploadFile] = File(default=None),
    text: Optional[str] = Form(default=None),
):
    async def event_generator():
        def emit(event, data):
            return f"event: {event}\ndata: {json.dumps(data)}\n\n"

        try:
            # --- STAGE: Upload / Input ---
            yield emit("progress", {"stage": "uploading", "status": "active"})
            await asyncio.sleep(0)

            if image:
                file_bytes = await image.read()
                raw_text = await asyncio.to_thread(extract_text_from_image, file_bytes)
                source_type = "image"
                source_filename = image.filename
            elif text:
                raw_text = text
                source_type = "text"
                source_filename = None
            else:
                yield emit("error", {"stage": "uploading", "message": "Provide an image file or text input"})
                return

            if not raw_text:
                yield emit("error", {"stage": "uploading", "message": "No text could be extracted from the input"})
                return

            yield emit("progress", {"stage": "uploading", "status": "complete"})
            await asyncio.sleep(0)

            # --- STAGE: OCR (only for images) ---
            if source_type == "image":
                yield emit("progress", {"stage": "ocr", "status": "active"})
                await asyncio.sleep(0)
                print(f"\nSTEP 1 - OCR: {len(raw_text)} chars extracted")
                yield emit("progress", {"stage": "ocr", "status": "complete"})
                await asyncio.sleep(0)
            else:
                yield emit("progress", {"stage": "ocr", "status": "complete"})
                await asyncio.sleep(0)

            # --- STAGE: Entity Extraction ---
            yield emit("progress", {"stage": "entity", "status": "active"})
            await asyncio.sleep(0)
            entities = await asyncio.to_thread(extract_entities, raw_text)
            yield emit("progress", {"stage": "entity", "status": "complete"})
            await asyncio.sleep(0)

            # --- STAGE: Technical Investigation ---
            yield emit("progress", {"stage": "technical", "status": "active"})
            await asyncio.sleep(0)
            investigation = await asyncio.to_thread(run_investigation, entities)
            yield emit("progress", {"stage": "technical", "status": "complete"})
            await asyncio.sleep(0)

            # --- STAGE: Content Analysis ---
            yield emit("progress", {"stage": "content_analysis", "status": "active"})
            await asyncio.sleep(0)
            content_analysis = await asyncio.to_thread(analyze_content, raw_text, entities)
            yield emit("progress", {"stage": "content_analysis", "status": "complete"})
            await asyncio.sleep(0)

            # --- STAGE: Gemma AI Reasoning ---
            yield emit("progress", {"stage": "reasoning", "status": "active"})
            await asyncio.sleep(0)
            raw_reasoning = await asyncio.to_thread(generate_reasoning_report, entities, investigation, content_analysis)
            ai_reasoning_parsed = await asyncio.to_thread(parse_reasoning, raw_reasoning)
            yield emit("progress", {"stage": "reasoning", "status": "complete"})
            await asyncio.sleep(0)

            # --- STAGE: Generate Report ---
            yield emit("progress", {"stage": "report", "status": "active"})
            await asyncio.sleep(0)
            technical = await asyncio.to_thread(_build_technical_checks, investigation, entities)
            risk_indicators = await asyncio.to_thread(_build_risk_indicators, technical, investigation)
            technical_evidence = await asyncio.to_thread(_build_technical_evidence, investigation)

            technical_risk = await asyncio.to_thread(_compute_technical_risk, investigation)
            content_risk = content_analysis.get("content_risk_score", 50)
            reasoning_risk = ai_reasoning_parsed.get("risk_score", 50)
            combined_risk = round((technical_risk * 0.35) + (content_risk * 0.30) + (reasoning_risk * 0.35))
            combined_risk = max(0, min(100, combined_risk))

            investigation_summary = investigation.get("_summary", {})
            verdict, confidence = _compute_verdict_and_confidence(combined_risk, ai_reasoning_parsed, investigation_summary)

            job_info = {
                "company": entities.get("company_name", ""),
                "title": entities.get("job_title", ""),
                "location": entities.get("location", ""),
                "salary": entities.get("salary", ""),
                "recruiter": entities.get("recruiter_name", ""),
                "email": entities.get("email", ""),
                "phone": entities.get("phone", ""),
                "website": entities.get("website", ""),
                "skills": ", ".join(entities.get("skills", [])) if isinstance(entities.get("skills"), list) else str(entities.get("skills", "")),
            }

            report_id = "local-" + str(id(job_info))

            result = {
                "verdict": verdict,
                "risk_score": combined_risk,
                "risk_breakdown": {
                    "technical_risk": technical_risk,
                    "content_risk": content_risk,
                    "reasoning_risk": reasoning_risk,
                },
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "report_id": report_id,
                "job_info": job_info,
                "ai_reasoning": ai_reasoning_parsed,
                "technical": technical,
                "risk_indicators": risk_indicators,
                "technical_evidence": technical_evidence,
                "content_analysis": content_analysis,
            }

            print(f"\nSTEP 7 - FINAL RESULT: verdict={verdict} score={combined_risk} technical={technical_risk} content={content_risk} reasoning={reasoning_risk}")
            yield emit("progress", {"stage": "report", "status": "complete"})
            await asyncio.sleep(0)
            yield emit("complete", result)

        except Exception as e:
            print(f"\nEXCEPTION in analyze_stream(): {type(e).__name__}: {e}")
            traceback.print_exc()
            yield emit("error", {"stage": "unknown", "message": f"{type(e).__name__}: {str(e)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/reports")
async def list_reports(limit: int = 50):
    return {"reports": []}


@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    raise HTTPException(status_code=404, detail="Report storage not configured")


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str):
    raise HTTPException(status_code=404, detail="Report storage not configured")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "SafeHire AI"}


@app.get("/api/health")
async def health():
    llm = get_llm_status()
    return {"status": "ok", "llm": llm}


@app.post("/api/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    try:
        sent = send_feedback_email(feedback)
        if sent:
            return {"status": "success", "message": "Feedback submitted successfully. Thank you!"}
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Feedback received but email delivery is not configured. Please contact us directly."}
        )
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process feedback")


@app.get("/debug/smtp")
async def debug_smtp():
    """Temporary debug endpoint — REMOVE after debugging."""
    host = "smtp.gmail.com"
    result = {"host": host, "dns": {}, "tcp": {}}

    # 1. DNS resolution — all addresses
    for fam in (socket.AF_INET, socket.AF_INET6):
        fam_name = "IPv4" if fam == socket.AF_INET else "IPv6"
        try:
            addrs = socket.getaddrinfo(host, None, fam, socket.SOCK_STREAM)
            result["dns"][fam_name] = [a[4][0] for a in addrs]
        except socket.gaierror as e:
            result["dns"][fam_name] = f"resolution failed: {e}"

    # 2. TCP connect test — port 587 and 465
    for port in (587, 465):
        try:
            conn = socket.create_connection((host, port), timeout=10)
            peer = conn.getpeername()
            conn.close()
            result["tcp"][str(port)] = {
                "status": "connected",
                "peer_ip": peer[0],
                "peer_port": peer[1],
            }
        except Exception as e:
            result["tcp"][str(port)] = {
                "status": "failed",
                "error": str(e),
                "errno": getattr(e, "errno", None),
            }

    return result


ROOT_DIR = Path(__file__).resolve().parent.parent


@app.get("/dashboard")
async def serve_dashboard():
    html_file = ROOT_DIR / "dashboard" / "dashboard.html"
    if html_file.exists():
        return FileResponse(str(html_file))
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/")
async def serve_index():
    index_file = ROOT_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="Index not found")


app.mount("/assets", StaticFiles(directory=str(ROOT_DIR / "assets")), name="assets")
app.mount("/dashboard", StaticFiles(directory=str(ROOT_DIR / "dashboard")), name="dashboard-static")
app.mount("/auth", StaticFiles(directory=str(ROOT_DIR / "auth")), name="auth")
app.mount("/navbar", StaticFiles(directory=str(ROOT_DIR / "navbar")), name="navbar-static")
