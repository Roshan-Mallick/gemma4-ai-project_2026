import re
import socket
import ssl
import json
import urllib.request
from datetime import datetime, timezone

import requests
import whois
import dns.resolver
import tldextract

from .config import FREE_EMAIL_PROVIDERS, DISPOSABLE_EMAIL_PROVIDERS
from .llm_client import call_gemma
from .abstract_api import validate_email, validate_phone, lookup_ip


def extract_domain(url_or_email):
    if not url_or_email:
        return None
    cleaned = str(url_or_email).strip().lower()
    if not cleaned:
        return None
    if "@" in cleaned:
        cleaned = cleaned.split("@")[-1]
    cleaned = re.sub(r"^https?://", "", cleaned)
    cleaned = cleaned.split("/")[0]
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    return cleaned.strip() or None


def _normalize(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value.strip() if isinstance(value, str) else value


def _company_to_slug(company_name):
    if not company_name:
        return None
    name = company_name.strip().lower()
    suffixes = [
        " corporation", " corp.", " corp", " inc.", " inc",
        " ltd.", " ltd", " llc", " co.", " co",
        " group", " industries", " international",
        " company", " companies",
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
    slug = re.sub(r"[^a-z0-9]", "", name)
    return slug if len(slug) >= 2 else None


# ============================================================================
# DOMAIN DISCOVERY
# ============================================================================

def discover_domain(entities):
    print(f"\n===== DOMAIN DISCOVERY =====")
    website = _normalize(entities.get("website"))
    email = _normalize(entities.get("email"))
    company = _normalize(entities.get("company_name"))
    print(f"  Website:  {repr(website)}")
    print(f"  Email:    {repr(email)}")
    print(f"  Company:  {repr(company)}")

    if website:
        domain = extract_domain(website)
        if domain:
            print(f"  Chosen Source: website")
            print(f"  Derived Domain: {domain}")
            return domain, "website"

    if email:
        domain = extract_domain(email)
        if domain:
            print(f"  Chosen Source: email")
            print(f"  Derived Domain: {domain}")
            return domain, "email"

    if company:
        print(f"  Attempting company name fallback...")
        domain = _verify_company_domain(company)
        if domain:
            print(f"  Chosen Source: company_name_verified")
            print(f"  Derived Domain: {domain}")
            return domain, "company_name_verified"

    print(f"  Chosen Source: none")
    print(f"  Derived Domain: None")
    return None, "none"


def _ask_gemma_for_website(company_name):
    if not company_name:
        return None
    prompt = (
        f"What is the official public website of the company '{company_name}'?\n"
        f"Reply with ONLY the bare domain, e.g. microsoft.com or ibm.com.\n"
        f"If you do not know or the company is obscure, reply with NONE."
    )
    try:
        print(f"  [GEMMA-WEBSITE] Asking Gemma for website of '{company_name}'...")
        response = call_gemma(prompt, max_tokens=30)
        response = response.strip().strip('"').strip("'").strip("`").strip(".")
        response = re.sub(r"^https?://", "", response)
        response = response.split("/")[0].strip()
        if response.lower() == "none" or not response or "." not in response:
            print(f"  [GEMMA-WEBSITE] Gemma replied: {repr(response)} (ignored)")
            return None
        domain = extract_domain(response)
        if domain and "." in domain:
            print(f"  [GEMMA-WEBSITE] Gemma suggested: {domain}")
            return domain
        print(f"  [GEMMA-WEBSITE] Could not parse domain from: {repr(response)}")
    except Exception as e:
        print(f"  [GEMMA-WEBSITE] Failed: {type(e).__name__}: {e}")
    return None


def _verify_domain_for_company(domain, company_name):
    if not domain or not company_name:
        return False
    print(f"    Verification of {domain} for '{company_name}':")
    try:
        socket.setdefaulttimeout(3)
        ip = socket.gethostbyname(domain)
        print(f"      DNS:      PASS ({ip})")
    except socket.gaierror:
        print(f"      DNS:      FAIL (no resolution)")
        return False

    try:
        resp = requests.get(
            f"https://{domain}", timeout=5,
            headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True,
        )
        print(f"      HTTP:     PASS (status={resp.status_code})")
    except Exception:
        try:
            resp = requests.get(
                f"http://{domain}", timeout=5,
                headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True,
            )
            print(f"      HTTP:     PASS (status={resp.status_code}, http)")
        except Exception as e2:
            print(f"      HTTP:     FAIL ({type(e2).__name__})")
            return False

    page_text = resp.text.lower()
    company_lower = company_name.lower()
    slug_name = _company_to_slug(company_name) or ""
    title = ""
    title_match = False
    slug_in_title = False
    slug_in_content = False
    title_tag = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
    if title_tag:
        title = title_tag.group(1).strip()
        title_lower = title.lower()
        title_match = company_lower in title_lower
        slug_in_title = slug_name and slug_name in title_lower
        print(f"      Page Title: {repr(title[:100])}")
    else:
        print(f"      Page Title: (none found)")
    company_found = company_lower in page_text
    slug_in_content = slug_name and slug_name in page_text
    print(f"      Company Match: full_in_title={title_match}, full_in_content={company_found}, slug_in_title={slug_in_title}, slug_in_content={slug_in_content}")

    if title_match or company_found or slug_in_title or slug_in_content:
        print(f"      RESULT: VERIFIED")
        return True
    print(f"      RESULT: NOT VERIFIED")
    return False


def _verify_company_domain(company_name):
    slug = _company_to_slug(company_name)
    gemma_domain = _ask_gemma_for_website(company_name)

    candidates = []
    if gemma_domain:
        candidates.append(gemma_domain)
    if slug:
        slug_domain = f"{slug}.com"
        if slug_domain not in candidates:
            candidates.append(slug_domain)

    for candidate in candidates:
        if _verify_domain_for_company(candidate, company_name):
            return candidate

    print(f"    No verified domain found for '{company_name}'")
    return None


def _live_web_check(domain):
    if not domain:
        return {"reachable": False, "status_code": None}
    url = f"https://{domain}" if not domain.startswith("http") else domain
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return {"reachable": True, "status_code": response.getcode()}
    except Exception as e:
        try:
            url_http = url.replace("https://", "http://")
            req = urllib.request.Request(url_http, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                return {"reachable": True, "status_code": response.getcode()}
        except Exception:
            return {"reachable": False, "error": str(e)}


# ============================================================================
# INVESTIGATION FUNCTIONS - each returns dict with "status" field
# status = "PASS" | "FAIL" | "UNKNOWN"
# ============================================================================

def investigate_domain(domain):
    print(f"\n  [WHOIS] domain={domain}")
    if not domain:
        print(f"  [WHOIS] UNKNOWN: no domain available")
        return {"status": "UNKNOWN", "message": "No domain available", "Registered": False, "Error": "No domain provided", "risk_delta": 0}
    result = {
        "status": "UNKNOWN",
        "Registered": False,
        "Domain Age": None,
        "Creation Date": None,
        "Expiry Date": None,
        "Registrar": None,
        "risk_delta": 0,
        "message": "",
    }
    try:
        url = f"https://rdap.org/domain/{domain}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode())
                result["Registered"] = True
                for event in data.get("events", []):
                    if event.get("eventAction") == "registration":
                        result["Creation Date"] = event.get("eventDate")
                    elif event.get("eventAction") == "expiration":
                        result["Expiry Date"] = event.get("eventDate")
                result["status"] = "PASS"
                result["risk_delta"] = -5
                result["message"] = "RDAP lookup successful"
                print(f"  [WHOIS] PASS: registered=True (RDAP)")
                return result
    except Exception as e:
        print(f"  [WHOIS] RDAP failed: {type(e).__name__}: {e}")
    try:
        w = whois.whois(domain)
        if w.domain_name:
            result["Registered"] = True
            result["Creation Date"] = str(
                w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
            )
            result["Expiry Date"] = str(
                w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
            )
            result["Registrar"] = w.registrar
            result["status"] = "PASS"
            result["risk_delta"] = -5
            result["message"] = "WHOIS lookup successful"
            print(f"  [WHOIS] PASS: registered=True (python-whois)")
        else:
            result["status"] = "FAIL"
            result["risk_delta"] = 10
            result["message"] = "WHOIS returned no domain name"
            print(f"  [WHOIS] FAIL: python-whois returned no domain_name")
    except Exception as e:
        print(f"  [WHOIS] python-whois failed: {type(e).__name__}: {e}")
        result["status"] = "UNKNOWN"
        result["risk_delta"] = 2
        result["message"] = f"WHOIS lookup blocked/timed out"
    return result


def query_dns(domain, record):
    try:
        answers = dns.resolver.resolve(domain, record)
        return [str(x) for x in answers]
    except Exception:
        return []


def query_mx_dns_over_https(domain):
    GOOGLE_DNS = "https://dns.google/resolve"
    CLOUDFLARE_DNS = "https://cloudflare-dns.com/dns-query"
    providers = [
        {"name": "Google DNS", "url": GOOGLE_DNS, "headers": {}},
        {"name": "Cloudflare DNS", "url": CLOUDFLARE_DNS,
         "headers": {"Accept": "application/dns-json"}},
    ]
    print(f"  [MX-DoH] ===== MX LOOKUP =====")
    print(f"  [MX-DoH] Primary: Google DNS")
    print(f"  [MX-DoH] Fallback: Cloudflare DNS")
    for i, provider in enumerate(providers):
        try:
            resp = requests.get(
                provider["url"],
                params={"name": domain, "type": "MX"},
                headers=provider["headers"],
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            if "Answer" in data and data["Answer"]:
                records = [a["data"] for a in data["Answer"] if a.get("type") == 15]
                print(f"  [MX-DoH] Selected Provider: {provider['name']}")
                print(f"  [MX-DoH] Status: PASS")
                for r in records:
                    print(f"  [MX-DoH]   {r}")
                return records
            else:
                print(f"  [MX-DoH] {provider['name']}: no MX records in response")
        except Exception as e:
            print(f"  [MX-DoH] {provider['name']} failed: {type(e).__name__}: {e}")
            if i == 0:
                print(f"  [MX-DoH] Google DNS failed. Switching to Cloudflare DNS...")
            continue
    print(f"  [MX-DoH] Status: UNKNOWN")
    print(f"  [MX-DoH] Reason: Unable to retrieve MX records from Google or Cloudflare.")
    return []


def investigate_dns(domain):
    print(f"\n  [DNS] domain={domain}")
    unknown_empty = {
        "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
        "A Record": [], "AAAA Record": [], "MX Record": [], "NS Record": [],
        "TXT Record": [], "SPF": False, "DMARC": False,
    }
    if not domain:
        print(f"  [DNS] UNKNOWN: no domain")
        return unknown_empty
    try:
        a_records = query_dns(domain, "A")
        print(f"  [DNS] A records: {a_records}")
        aaaa_records = query_dns(domain, "AAAA")
        mx_records = query_mx_dns_over_https(domain)
        print(f"  [DNS] MX records: {mx_records}")
        ns_records = query_dns(domain, "NS")
        txt = query_dns(domain, "TXT")
        print(f"  [DNS] TXT records: {txt[:3]}")
        spf = any("v=spf1" in t.lower() for t in txt)
        print(f"  [DNS] SPF: {spf}")
        dmarc = False
        try:
            d = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            dmarc = len(d) > 0
        except Exception:
            pass
        print(f"  [DNS] DMARC: {dmarc}")
        has_a = len(a_records) > 0
        has_mx = len(mx_records) > 0
        if has_a and has_mx:
            status, risk_delta = "PASS", -5
        elif has_a:
            status, risk_delta = "PASS", -2
        else:
            status, risk_delta = "FAIL", 10
        print(f"  [DNS] {status}")
        return {
            "status": status, "risk_delta": risk_delta,
            "A Record": a_records, "AAAA Record": aaaa_records,
            "MX Record": mx_records, "NS Record": ns_records,
            "TXT Record": txt, "SPF": spf, "DMARC": dmarc,
        }
    except Exception as e:
        print(f"  [DNS] UNKNOWN: {type(e).__name__}: {e}")
        return {**unknown_empty, "message": f"DNS lookup failed"}


def investigate_ssl(domain):
    print(f"\n  [SSL] domain={domain}")
    result = {
        "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
        "HTTPS Available": False, "Certificate Valid": False,
        "Issuer": None, "Valid From": None, "Valid Until": None,
        "Days Remaining": None, "TLS Version": None,
    }
    if not domain:
        print(f"  [SSL] UNKNOWN: no domain")
        return result
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                result["HTTPS Available"] = True
                result["TLS Version"] = ssock.version()
                issuer = dict(x[0] for x in cert["issuer"])
                result["Issuer"] = issuer.get("organizationName")
                from dateutil.parser import parse
                start = parse(cert["notBefore"])
                end = parse(cert["notAfter"])
                result["Valid From"] = str(start)
                result["Valid Until"] = str(end)
                result["Certificate Valid"] = start <= datetime.now(timezone.utc) <= end
                result["Days Remaining"] = (end - datetime.now(timezone.utc)).days
                if result["Certificate Valid"]:
                    result["status"] = "PASS"
                    result["risk_delta"] = -10
                    result["message"] = "Valid SSL certificate"
                else:
                    result["status"] = "FAIL"
                    result["risk_delta"] = 20
                    result["message"] = "SSL certificate expired or not yet valid"
                print(f"  [SSL] {result['status']}: issuer={result['Issuer']}, valid={result['Certificate Valid']}, tls={result['TLS Version']}")
    except Exception as e:
        print(f"  [SSL] FAIL: {type(e).__name__}: {e}")
        result["status"] = "FAIL"
        result["risk_delta"] = 10
        result["message"] = f"SSL connection failed: {type(e).__name__}"
    return result


def investigate_email(email):
    print(f"\n  [EMAIL] email={email}")
    domain = extract_domain(email)
    print(f"  [EMAIL] extracted domain={domain}")
    if not email or not domain:
        msg = "No email provided" if not email else "Could not extract domain from email"
        print(f"  [EMAIL] UNKNOWN: {msg}")
        return {
            "status": "UNKNOWN", "risk_delta": 0, "message": msg,
            "Domain": domain, "Registered": None, "Domain Age": None,
            "Free Provider": False, "Disposable Provider": False,
            "MX Exists": False, "SPF": False, "DMARC": False,
            "Typosquatting": False, "Risk Score": 0,
            "abstract_api": None,
        }

    domain_info = investigate_domain(domain)
    dns_info = investigate_dns(domain)
    abstract_result = validate_email(email)

    risk = 0
    if domain in FREE_EMAIL_PROVIDERS:
        risk += 30
    if domain in DISPOSABLE_EMAIL_PROVIDERS:
        risk += 50
    mx_records = dns_info.get("MX Record", [])
    if not mx_records:
        risk += 20
    if not dns_info.get("SPF"):
        risk += 10
    if not dns_info.get("DMARC"):
        risk += 10

    if abstract_result:
        if abstract_result["deliverability"] == "UNDELIVERABLE":
            risk += 30
        elif abstract_result["deliverability"] == "UNKNOWN":
            risk += 5
        qs = abstract_result.get("quality_score")
        if qs is not None:
            try:
                qs_f = float(qs)
                if qs_f < 0.3:
                    risk += 20
                elif qs_f < 0.6:
                    risk += 10
            except (ValueError, TypeError):
                pass
        if abstract_result.get("is_disposable_email"):
            risk += 40
        if abstract_result.get("is_free_email") and not abstract_result.get("is_role_email"):
            risk += 15
        if abstract_result.get("is_role_email"):
            risk += 5
        if abstract_result.get("is_catchall_email"):
            risk += 10
        if abstract_result.get("is_smtp_valid") is False:
            risk += 15
        if abstract_result.get("is_mx_found") is False:
            risk += 15
        if abstract_result.get("autocorrect"):
            risk += 20

    typo = False
    famous = ["google.com", "amazon.com", "microsoft.com", "linkedin.com"]
    for f in famous:
        if domain and domain != f and domain.replace("-", "") == f.replace("-", ""):
            typo = True
            risk += 30

    risk_score = min(risk, 100)
    if risk_score == 0:
        status, risk_delta = "PASS", -5
    elif risk_score >= 50:
        status, risk_delta = "FAIL", 15
    else:
        status, risk_delta = "FAIL", 5

    result = {
        "status": status, "risk_delta": risk_delta,
        "Domain": domain,
        "Registered": domain_info.get("Registered"),
        "Domain Age": domain_info.get("Domain Age"),
        "Free Provider": domain in FREE_EMAIL_PROVIDERS if domain else False,
        "Disposable Provider": domain in DISPOSABLE_EMAIL_PROVIDERS if domain else False,
        "MX Exists": len(mx_records) > 0,
        "SPF": dns_info.get("SPF", False),
        "DMARC": dns_info.get("DMARC", False),
        "Typosquatting": typo,
        "Risk Score": risk_score,
        "abstract_api": abstract_result,
    }
    print(f"  [EMAIL] {status}: domain={domain}, risk={risk_score}, abstract_api={'yes' if abstract_result else 'no'}")
    return result


def investigate_salary(salary_text):
    if not salary_text:
        return {"Salary Text": "", "Suspicious Salary": False}
    salary = salary_text.lower()
    suspicious = any(x in salary for x in ["earn", "per day", "daily income", "guaranteed", "instant"])
    return {"Salary Text": salary_text, "Suspicious Salary": suspicious}


def investigate_phone(phone):
    print(f"\n  [PHONE] phone={phone}")
    if not phone:
        print(f"  [PHONE] UNKNOWN: no phone number")
        return {
            "status": "UNKNOWN", "risk_delta": 0, "message": "No phone number provided",
            "is_valid": None, "line_type": None, "is_voip": None,
            "country": None, "risk_level": None, "is_disposable": None,
            "is_abuse_detected": None, "total_breaches": 0, "abstract_api": None,
        }
    abstract_result = validate_phone(phone)
    risk = 0
    if abstract_result:
        if abstract_result.get("is_valid") is False:
            risk += 20
        if abstract_result.get("is_voip"):
            risk += 30
        if abstract_result.get("is_disposable"):
            risk += 40
        if abstract_result.get("is_abuse_detected"):
            risk += 35
        rl = abstract_result.get("risk_level")
        if rl == "high":
            risk += 25
        elif rl == "medium":
            risk += 10
        tb = abstract_result.get("total_breaches", 0)
        if tb > 0:
            risk += min(20, tb * 5)
        lt = abstract_result.get("line_type")
        if lt == "toll_free":
            risk += 15
        elif lt == "premium_rate":
            risk += 25
    risk_score = min(risk, 100)
    if risk_score == 0:
        status, risk_delta = "PASS", -3
    elif risk_score >= 50:
        status, risk_delta = "FAIL", 10
    else:
        status, risk_delta = "FAIL", 3
    result = {
        "status": status, "risk_delta": risk_delta,
        "is_valid": abstract_result.get("is_valid") if abstract_result else None,
        "line_type": abstract_result.get("line_type") if abstract_result else None,
        "line_status": abstract_result.get("line_status") if abstract_result else None,
        "is_voip": abstract_result.get("is_voip", False) if abstract_result else None,
        "carrier_name": abstract_result.get("carrier_name") if abstract_result else None,
        "country": abstract_result.get("country") if abstract_result else None,
        "country_code": abstract_result.get("country_code") if abstract_result else None,
        "region": abstract_result.get("region") if abstract_result else None,
        "city": abstract_result.get("city") if abstract_result else None,
        "risk_level": abstract_result.get("risk_level", "unknown") if abstract_result else "unknown",
        "is_disposable": abstract_result.get("is_disposable", False) if abstract_result else None,
        "is_abuse_detected": abstract_result.get("is_abuse_detected", False) if abstract_result else None,
        "total_breaches": abstract_result.get("total_breaches", 0) if abstract_result else 0,
        "Risk Score": risk_score,
        "abstract_api": abstract_result,
    }
    print(f"  [PHONE] {status}: risk={risk_score}, voip={result['is_voip']}, "
          f"disposable={result['is_disposable']}, abuse={result['is_abuse_detected']}")
    return result


def investigate_ip_geolocation(domain):
    print(f"\n  [IP GEO] domain={domain}")
    if not domain:
        print(f"  [IP GEO] UNKNOWN: no domain")
        return {
            "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
            "ip_address": None, "city": None, "region": None, "country": None,
            "is_vpn": None, "isp": None, "abstract_api": None,
        }
    try:
        answers = dns.resolver.resolve(domain, "A")
        ip_address = str(answers[0])
    except Exception:
        print(f"  [IP GEO] UNKNOWN: could not resolve domain to IP")
        return {
            "status": "UNKNOWN", "risk_delta": 0, "message": "Could not resolve domain to IP",
            "ip_address": None, "city": None, "region": None, "country": None,
            "is_vpn": None, "isp": None, "abstract_api": None,
        }
    print(f"  [IP GEO] resolved IP: {ip_address}")
    abstract_result = lookup_ip(ip_address)
    risk = 0
    if abstract_result:
        if abstract_result.get("is_vpn"):
            risk += 25
    risk_score = min(risk, 100)
    if risk_score == 0:
        status, risk_delta = "PASS", -2
    elif risk_score >= 25:
        status, risk_delta = "FAIL", 8
    else:
        status, risk_delta = "UNKNOWN", 0
    result = {
        "status": status, "risk_delta": risk_delta,
        "ip_address": ip_address,
        "city": abstract_result.get("city") if abstract_result else None,
        "region": abstract_result.get("region") if abstract_result else None,
        "country": abstract_result.get("country") if abstract_result else None,
        "country_code": abstract_result.get("country_code") if abstract_result else None,
        "continent": abstract_result.get("continent") if abstract_result else None,
        "latitude": abstract_result.get("latitude") if abstract_result else None,
        "longitude": abstract_result.get("longitude") if abstract_result else None,
        "is_vpn": abstract_result.get("is_vpn", False) if abstract_result else None,
        "isp": abstract_result.get("isp") if abstract_result else None,
        "connection_type": abstract_result.get("connection_type") if abstract_result else None,
        "organization": abstract_result.get("organization") if abstract_result else None,
        "Risk Score": risk_score,
        "abstract_api": abstract_result,
    }
    print(f"  [IP GEO] {status}: ip={ip_address}, city={result['city']}, "
          f"country={result['country']}, vpn={result['is_vpn']}")
    return result


def investigate_robots_txt(domain):
    result = {
        "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
        "found": False, "size_bytes": 0, "disallow_count": 0,
        "sitemaps_found": 0, "blocks_all_crawlers": False,
        "is_default_cms": False, "suspicious_patterns": [],
    }
    if not domain:
        print(f"  [ROBOTS] UNKNOWN: no domain")
        return result
    url = f"https://{domain}/robots.txt"
    print(f"  [ROBOTS] checking {url}")
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})
        if resp.status_code != 200:
            print(f"  [ROBOTS] UNKNOWN: status={resp.status_code}")
            result["status"] = "UNKNOWN"
            result["risk_delta"] = 2
            result["message"] = f"HTTP {resp.status_code}"
            return result
        content = resp.text
        result["found"] = True
        result["size_bytes"] = len(content)
        lines = content.lower().splitlines()
        disallow_all = False
        for line in lines:
            line = line.strip()
            if line.startswith("disallow:") and line.split(":", 1)[1].strip() == "/":
                disallow_all = True
            if line.startswith("disallow:"):
                result["disallow_count"] += 1
            if line.startswith("sitemap:"):
                result["sitemaps_found"] += 1
        result["blocks_all_crawlers"] = disallow_all
        if len(content) < 50:
            result["suspicious_patterns"].append("Very small robots.txt")
        if result["sitemaps_found"] == 0:
            result["suspicious_patterns"].append("No sitemap referenced")
        if disallow_all:
            result["suspicious_patterns"].append("Blocks all crawlers")
        if disallow_all:
            result["status"] = "FAIL"
            result["risk_delta"] = 10
            result["message"] = "robots.txt blocks all crawlers"
        else:
            result["status"] = "PASS"
            result["risk_delta"] = -2
            result["message"] = "robots.txt present and normal"
        print(f"  [ROBOTS] {result['status']}: size={result['size_bytes']}, disallow={result['disallow_count']}")
    except Exception as e:
        print(f"  [ROBOTS] UNKNOWN: {type(e).__name__}: {e}")
        result["status"] = "UNKNOWN"
        result["risk_delta"] = 2
        result["message"] = f"Request failed"
    return result


def investigate_sitemap(domain):
    result = {
        "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
        "found": False, "url_count": 0, "last_modified": None,
        "is_sitemap_index": False, "same_domain_urls": True,
        "suspicious_patterns": [],
    }
    if not domain:
        print(f"  [SITEMAP] UNKNOWN: no domain")
        return result
    for path in ["/sitemap.xml", "/sitemap_index.xml"]:
        try:
            url = f"https://{domain}{path}"
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})
            if resp.status_code == 200 and ("<urlset" in resp.text.lower() or "<sitemapindex" in resp.text.lower()):
                content = resp.text
                result["found"] = True
                result["is_sitemap_index"] = "<sitemapindex" in content.lower()
                import re as _re
                urls = _re.findall(r"<loc>(.*?)</loc>", content)
                result["url_count"] = len(urls)
                lastmods = _re.findall(r"<lastmod>(.*?)</lastmod>", content)
                if lastmods:
                    result["last_modified"] = lastmods[-1]
                if urls:
                    non_matching = [u for u in urls[:50] if domain not in u]
                    result["same_domain_urls"] = len(non_matching) == 0
                if result["url_count"] == 0:
                    result["suspicious_patterns"].append("Empty sitemap")
                if not result["same_domain_urls"]:
                    result["suspicious_patterns"].append("URLs point to different domains")
                if result["last_modified"]:
                    try:
                        from dateutil.parser import parse as dtparse
                        mod_date = dtparse(result["last_modified"])
                        if (datetime.now(timezone.utc) - mod_date.replace(tzinfo=timezone.utc)).days > 365:
                            result["suspicious_patterns"].append("Last modified > 1 year ago")
                    except Exception:
                        pass
                if result["suspicious_patterns"]:
                    result["status"] = "FAIL"
                    result["risk_delta"] = 5
                    result["message"] = "Sitemap has suspicious patterns"
                else:
                    result["status"] = "PASS"
                    result["risk_delta"] = -2
                    result["message"] = "Sitemap present and normal"
                break
        except Exception:
            pass
    if not result["found"]:
        result["suspicious_patterns"].append("No sitemap found")
        result["status"] = "UNKNOWN"
        result["risk_delta"] = 2
        result["message"] = "No sitemap found"
        print(f"  [SITEMAP] UNKNOWN: no sitemap found")
    else:
        print(f"  [SITEMAP] {result['status']}: urls={result['url_count']}")
    return result


def investigate_http_headers(domain):
    BOT_PROTECTION_SERVERS = {"AkamaiNetStorage", "AkamaiGHost", "CloudFront", "Cloudflare", "Varnish", "nginx"}
    BOT_PROTECTION_CODES = {403, 406, 429, 503}

    result = {
        "status": "UNKNOWN", "risk_delta": 0, "message": "No domain available",
        "status_code": None, "server": None, "security_headers": {},
        "redirect_chain": [], "final_url": None,
    }
    if not domain:
        print(f"  [HTTP] UNKNOWN: no domain")
        return result
    url = f"https://{domain}"
    print(f"  [HTTP] checking {url}")
    try:
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["final_url"] = resp.url
        result["server"] = resp.headers.get("Server")
        result["security_headers"] = {
            "x_frame_options": "X-Frame-Options" in resp.headers,
            "x_content_type_options": "X-Content-Type-Options" in resp.headers,
            "csp": "Content-Security-Policy" in resp.headers,
            "hsts": "Strict-Transport-Security" in resp.headers,
        }
        if len(resp.history) > 0:
            result["redirect_chain"] = [r.url for r in resp.history]
        if resp.status_code == 200:
            result["status"] = "PASS"
            result["risk_delta"] = -3
            result["message"] = "HTTP 200 OK"
        elif resp.status_code in BOT_PROTECTION_CODES:
            server_name = result["server"] or ""
            is_bot_protection = any(bp.lower() in server_name.lower() for bp in BOT_PROTECTION_SERVERS)
            if is_bot_protection:
                result["status"] = "PASS"
                result["risk_delta"] = -1
                result["message"] = f"HTTP {resp.status_code} (bot protection: {server_name})"
            else:
                result["status"] = "FAIL"
                result["risk_delta"] = 5
                result["message"] = f"HTTP {resp.status_code}"
        elif 200 <= resp.status_code < 400:
            result["status"] = "PASS"
            result["risk_delta"] = -2
            result["message"] = f"HTTP {resp.status_code}"
        else:
            result["status"] = "FAIL"
            result["risk_delta"] = 5
            result["message"] = f"HTTP {resp.status_code}"
        print(f"  [HTTP] {result['status']}: status={result['status_code']}, server={result['server']}")
    except Exception as e:
        print(f"  [HTTP] UNKNOWN: {type(e).__name__}: {e}")
        result["status"] = "UNKNOWN"
        result["risk_delta"] = 2
        result["message"] = f"{type(e).__name__}: {str(e)[:80]}"
    return result


# ============================================================================
# MAIN INVESTIGATION
# ============================================================================

def run_investigation(entities):
    print(f"\n===== TECHNICAL INVESTIGATION =====")
    company_name = _normalize(entities.get("company_name"))
    website = _normalize(entities.get("website"))
    email = _normalize(entities.get("email"))
    phone = _normalize(entities.get("phone"))
    salary = entities.get("salary")

    target_domain, domain_source = discover_domain(entities)

    report = {}
    if target_domain:
        print(f"\n  --- Running domain checks for: {target_domain} (source: {domain_source}) ---")
        report["Domain"] = investigate_domain(target_domain)
        report["DNS"] = investigate_dns(target_domain)
        report["SSL"] = investigate_ssl(target_domain)
        report["Robots.txt"] = investigate_robots_txt(target_domain)
        report["Sitemap"] = investigate_sitemap(target_domain)
        report["HTTP Headers"] = investigate_http_headers(target_domain)
        report["IP Geolocation"] = investigate_ip_geolocation(target_domain)
    else:
        print(f"\n  NO DOMAIN FOUND. All domain checks will be UNKNOWN.")
        unknown = {"status": "UNKNOWN", "risk_delta": 0, "message": "No verified domain available"}
        report["Domain"] = {**unknown, "Registered": False}
        report["DNS"] = {**unknown, "A Record": [], "AAAA Record": [], "MX Record": [], "NS Record": [], "TXT Record": [], "SPF": False, "DMARC": False}
        report["SSL"] = {**unknown, "HTTPS Available": False, "Certificate Valid": False, "Issuer": None, "Valid From": None, "Valid Until": None, "Days Remaining": None, "TLS Version": None}
        report["Robots.txt"] = {**unknown, "found": False, "size_bytes": 0, "disallow_count": 0, "sitemaps_found": 0, "blocks_all_crawlers": False, "is_default_cms": False, "suspicious_patterns": []}
        report["Sitemap"] = {**unknown, "found": False, "url_count": 0, "last_modified": None, "is_sitemap_index": False, "same_domain_urls": True, "suspicious_patterns": []}
        report["HTTP Headers"] = {**unknown, "status_code": None, "server": None, "security_headers": {}, "redirect_chain": [], "final_url": None}
        report["IP Geolocation"] = {**unknown, "ip_address": None, "city": None, "region": None, "country": None, "is_vpn": None, "isp": None}

    report["Email"] = investigate_email(email)
    report["Phone"] = investigate_phone(phone)
    report["Company"] = {
        "Company Name": company_name,
        "Website Domain": target_domain,
        "Domain Source": domain_source,
        "Email Domain Match": extract_domain(website) == extract_domain(email) if (website and email) else True,
        "Website Reachable": report["SSL"].get("HTTPS Available", False),
    }
    report["Salary"] = investigate_salary(salary)

    if target_domain:
        web_status = _live_web_check(target_domain)
        report["Live_Web_Verification"] = web_status
    else:
        report["Live_Web_Verification"] = {"reachable": False, "status_code": None}

    statuses = []
    for key in ["Domain", "DNS", "SSL", "Robots.txt", "Sitemap", "HTTP Headers", "Email", "Phone", "IP Geolocation"]:
        item = report.get(key, {})
        statuses.append(item.get("status", "UNKNOWN"))
    unknown_count = statuses.count("UNKNOWN")
    pass_count = statuses.count("PASS")
    fail_count = statuses.count("FAIL")
    report["_summary"] = {
        "unknown_count": unknown_count,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "domain_source": domain_source,
        "target_domain": target_domain,
    }

    print(f"\n===== INVESTIGATION RESULT =====")
    print(f"  Summary: {pass_count} PASS, {fail_count} FAIL, {unknown_count} UNKNOWN")
    print(f"===== END INVESTIGATION =====\n")
    return report
