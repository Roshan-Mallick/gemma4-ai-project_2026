import logging
from .config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)
_client = None


def _get_client():
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase not configured, report storage disabled")
            return None
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def save_report(data: dict, user_id: str = None) -> str:
    client = _get_client()
    if not client:
        logger.warning("Supabase unavailable, report not saved")
        return "local-" + str(id(data))
    payload = {**data}
    if user_id:
        payload["user_id"] = user_id
    resp = client.table("reports").insert(payload).execute()
    return resp.data[0]["id"] if resp.data else None


def get_report(report_id: str) -> dict:
    client = _get_client()
    if not client:
        return None
    resp = client.table("reports").select("*").eq("id", report_id).execute()
    return resp.data[0] if resp.data else None


def list_reports(limit: int = 50, user_id: str = None) -> list:
    client = _get_client()
    if not client:
        return []
    query = client.table("reports").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    resp = query.execute()
    return resp.data or []


def delete_report(report_id: str, user_id: str = None) -> bool:
    client = _get_client()
    if not client:
        return False
    query = client.table("reports").delete().eq("id", report_id)
    if user_id:
        query = query.eq("user_id", user_id)
    resp = query.execute()
    return True
