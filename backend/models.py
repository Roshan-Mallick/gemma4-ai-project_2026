from pydantic import BaseModel
from typing import Optional


class JobInfo(BaseModel):
    company: str = ""
    title: str = ""
    location: str = ""
    salary: str = ""
    recruiter: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    skills: str = ""


class AIReasoning(BaseModel):
    risk_score: int = 50
    verdict: str = "CAUTION"
    red_flags: list[str] = []
    green_flags: list[str] = []
    explanation: str = ""


class TechnicalChecks(BaseModel):
    domain_registered: bool = False
    website_reachable: bool = False
    https_enabled: bool = False
    ssl_valid: bool = False
    mx_record: bool = False
    spf_record: bool = False
    dmarc_record: bool = False
    email_domain_match: bool = False
    typosquatting: bool = False
    disposable_email: bool = False
    free_email: bool = False
    live_verification: bool = False
    robots_txt_found: bool = False
    robots_txt_suspicious: bool = False
    sitemap_found: bool = False
    sitemap_suspicious: bool = False


class RiskIndicators(BaseModel):
    free_email: str = "No"
    disposable_email: str = "No"
    suspicious_salary: str = "No"
    spf_missing: str = "No"
    dmarc_missing: str = "No"
    https_enabled: str = "No"
    ssl_valid: str = "No"
    domain_age: str = "Unknown"
    robots_txt: str = "Unknown"
    sitemap: str = "Unknown"


class AnalysisResponse(BaseModel):
    verdict: str
    risk_score: int
    confidence: str
    timestamp: str
    report_id: Optional[str] = None
    job_info: JobInfo
    ai_reasoning: AIReasoning
    technical: TechnicalChecks
    risk_indicators: RiskIndicators
    technical_evidence: dict
