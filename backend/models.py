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
    disposable_email: bool = False
    free_email: bool = False
    live_verification: bool = False
    phone_valid: bool = False


class RiskIndicators(BaseModel):
    domain_registered: str = "No"
    https_enabled: str = "No"
    ssl_valid: str = "No"
    mx_record: str = "No"
    spf_record: str = "No"
    dmarc_record: str = "No"
    email_domain_match: str = "No"
    phone_valid: str = "No"
    disposable_email: str = "No"
    free_email: str = "No"
    suspicious_salary: str = "No"
    domain_age: str = "Unknown"
    domain_source: str = "unknown"
    checks_pass: int = 0
    checks_fail: int = 0
    checks_unknown: int = 0


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
