import requests
from .config import (
    ABSTRACT_EMAIL_API_KEY, ABSTRACT_EMAIL_API_URL,
    ABSTRACT_PHONE_API_KEY, ABSTRACT_PHONE_API_URL,
    ABSTRACT_IP_API_KEY, ABSTRACT_IP_API_URL,
)

TIMEOUT = 10


def validate_email(email):
    if not email or not ABSTRACT_EMAIL_API_KEY:
        print(f"  [ABSTRACT EMAIL] SKIPPED: no email or no API key")
        return None
    print(f"  [ABSTRACT EMAIL] validating: {email}")
    try:
        resp = requests.get(ABSTRACT_EMAIL_API_URL, params={
            "api_key": ABSTRACT_EMAIL_API_KEY,
            "email": email,
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        result = {
            "email": data.get("email", email),
            "deliverability": data.get("deliverability", "UNKNOWN"),
            "quality_score": data.get("quality_score"),
            "is_valid_format": _extract_bool(data.get("is_valid_format")),
            "is_free_email": _extract_bool(data.get("is_free_email")),
            "is_disposable_email": _extract_bool(data.get("is_disposable_email")),
            "is_role_email": _extract_bool(data.get("is_role_email")),
            "is_catchall_email": _extract_bool(data.get("is_catchall_email")),
            "is_mx_found": _extract_bool(data.get("is_mx_found")),
            "is_smtp_valid": _extract_bool(data.get("is_smtp_valid")),
            "autocorrect": data.get("autocorrect", ""),
        }
        print(f"  [ABSTRACT EMAIL] deliverability={result['deliverability']}, "
              f"quality={result['quality_score']}, free={result['is_free_email']}, "
              f"disposable={result['is_disposable_email']}, role={result['is_role_email']}, "
              f"smtp={result['is_smtp_valid']}, catchall={result['is_catchall_email']}")
        return result
    except Exception as e:
        print(f"  [ABSTRACT EMAIL] ERROR: {type(e).__name__}: {e}")
        return None


def validate_phone(phone_number):
    if not phone_number or not ABSTRACT_PHONE_API_KEY:
        print(f"  [ABSTRACT PHONE] SKIPPED: no phone or no API key")
        return None
    cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    print(f"  [ABSTRACT PHONE] validating: {cleaned}")
    try:
        resp = requests.get(ABSTRACT_PHONE_API_URL, params={
            "api_key": ABSTRACT_PHONE_API_KEY,
            "phone_number": cleaned,
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        validation = data.get("phone_validation", {})
        carrier = data.get("phone_carrier", {})
        location = data.get("phone_location", {})
        risk = data.get("phone_risk", {})
        breaches = data.get("phone_breaches", {})
        result = {
            "phone_number": data.get("phone_number", cleaned),
            "is_valid": validation.get("is_valid"),
            "line_status": validation.get("line_status"),
            "is_voip": validation.get("is_voip", False),
            "carrier_name": carrier.get("name"),
            "line_type": carrier.get("line_type"),
            "country": location.get("country_name"),
            "country_code": location.get("country_code"),
            "region": location.get("region"),
            "city": location.get("city"),
            "risk_level": risk.get("risk_level", "unknown"),
            "is_disposable": risk.get("is_disposable", False),
            "is_abuse_detected": risk.get("is_abuse_detected", False),
            "total_breaches": breaches.get("total_breaches", 0),
        }
        print(f"  [ABSTRACT PHONE] valid={result['is_valid']}, type={result['line_type']}, "
              f"voip={result['is_voip']}, risk={result['risk_level']}, "
              f"abuse={result['is_abuse_detected']}, breaches={result['total_breaches']}")
        return result
    except Exception as e:
        print(f"  [ABSTRACT PHONE] ERROR: {type(e).__name__}: {e}")
        return None


def lookup_ip(ip_address):
    if not ip_address or not ABSTRACT_IP_API_KEY:
        print(f"  [ABSTRACT IP] SKIPPED: no IP or no API key")
        return None
    print(f"  [ABSTRACT IP] looking up: {ip_address}")
    try:
        resp = requests.get(ABSTRACT_IP_API_URL, params={
            "api_key": ABSTRACT_IP_API_KEY,
            "ip_address": ip_address,
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        security = data.get("security", {})
        connection = data.get("connection", {})
        timezone = data.get("timezone", {})
        result = {
            "ip_address": data.get("ip_address", ip_address),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "country_code": data.get("country_code"),
            "continent": data.get("continent"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "is_vpn": security.get("is_vpn", False),
            "isp": connection.get("isp_name"),
            "connection_type": connection.get("connection_type"),
            "organization": connection.get("organization_name"),
            "timezone": timezone.get("name"),
        }
        print(f"  [ABSTRACT IP] city={result['city']}, country={result['country']}, "
              f"vpn={result['is_vpn']}, isp={result['isp']}")
        return result
    except Exception as e:
        print(f"  [ABSTRACT IP] ERROR: {type(e).__name__}: {e}")
        return None


def _extract_bool(obj):
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return obj.get("value")
    return None
