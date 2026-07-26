# SafeHire AI

### AI-Powered Job Scam Detection Platform Built with Gemma 4

**Selected Theme:** Protecting People Online

**Build with Gemma Hackathon 2026**

---

## Live Deployment

| Layer | Platform | URL |
|-------|----------|-----|
| **Backend** (API) | Render (Docker) | [gemma4-ai-project-2026-azb0.onrender.com](https://gemma4-ai-project-2026-azb0.onrender.com) |
| **Frontend** (UI) | Vercel | [safehire-ai.vercel.app](https://safehire-ai.vercel.app) |

The backend is containerized via `render/Dockerfile` and deploys automatically on each push to `main`. The frontend is a static site served by Vercel.

---

## Why SafeHire AI

| | |
|---|---|
| **Problem Scale** | $300M+ lost to job scams annually in the US — a quantifiable, relatable, real-world problem |
| **Technical Depth** | 12 independent technical checks (WHOIS, DNS MX/SPF/DMARC, SSL, HTTP headers, email/phone validation) layered with LLM reasoning — not a single API call wrapped in a UI |
| **Architecture** | Clean separation of concerns: OCR → Entity Extraction → Technical Investigation → Content Analysis → AI Reasoning → Weighted Scoring. Each stage is independently testable and replaceable |
| **Gemma 4 Integration** | Used in 4 distinct pipeline stages — entity extraction, content analysis, cybersecurity reasoning, and domain discovery. Not a token gesture; Gemma 4 is the reasoning backbone |
| **Real Engineering** | SSE event-loop starvation fixed with `asyncio.to_thread()` + socket flush. Regex fallback for LLM extraction failures. Iterative weight tuning for 35/30/35 risk scoring. Actual debugging, not fabricated difficulty |
| **Scoped Correctly** | FastAPI + vanilla JS frontend. Achievable in hackathon timeframes. No framework overhead, no unnecessary complexity |

---

## What Problem We Are Solving

Job scams cost victims over $300 million annually in the US alone. Scammers impersonate legitimate companies, create fake job listings, and exploit job seekers who are desperate for work. Traditional spam filters focus on email content but miss the deeper technical signals: unregistered domains, missing DNS records, invalid SSL certificates, and disposable email addresses. Job seekers have no reliable way to verify whether a posting is legitimate before sharing sensitive personal and financial information.

**SafeHire AI** solves this by combining deep technical investigation with Gemma 4's reasoning capabilities to produce an evidence-based risk verdict for any job posting — in seconds.

---

## Solution Overview

A user pastes a job posting text or uploads a screenshot. The system:

1. Runs OCR (Tesseract) to extract text from images
2. Extracts entities (company name, email, phone, domain, salary, etc.) using **Gemma 4 + regex fallback**
3. Performs 12 technical checks (WHOIS, DNS MX/SPF/DMARC, SSL, HTTP headers, email validation, phone validation)
4. Analyzes content for scam indicators (unrealistic salary, urgency pressure, PII requests)
5. Asks **Gemma 4** to reason over all evidence as a cybersecurity analyst
6. Computes a combined risk score (35% technical + 30% content + 35% reasoning)
7. Returns a verdict: **SAFE**, **SUSPICIOUS**, or **SCAM**

All progress streams live to the browser via Server-Sent Events.

---

## Project Architecture

```
┌─────────────────┐    ┌──────────────────────────────────────┐
│ Frontend        │───▶│           FastAPI Backend            │
│ (Vercel)        │    │         (Render Docker)              │
│ Vanilla JS      │    │                                      │
│ SSE Stream      │◀───│  OCR → Entities → Investigation →    │
└─────────────────┘    │ Content Analysis → Gemma 4 Reasoning │
                       └──────────────────────────────────────┘
                                            │
                                            ▼
                                      ┌──────────┐
                                      │OpenRouter│
                                      │ (Gemma 4)│
                                      └──────────┘
```

- **Backend:** Python 3.12, FastAPI, Uvicorn (containerized via Docker on Render)
- **Frontend:** Vanilla HTML, CSS, JavaScript (static site on Vercel)
- **LLM:** Gemma 4 31B via OpenRouter
- **External APIs:** Abstract API for email/phone validation
- **OCR:** Tesseract via pytesseract

---

## Gemma 4 Integration

Gemma 4 is the core intelligence powering every stage of the pipeline:

**Entity Extraction:** Gemma 4 parses unstructured OCR text to extract company names, recruiter names, emails, phone numbers, salaries, job titles, and domains. A regex fallback handles cases where the LLM is unavailable.

**Content Analysis:** Gemma 4 evaluates the posting against 10 content risk factors — salary realism, email legitimacy, grammar quality, urgency/pressure language, payment requests, interview process validity, contact quality, company verification, timeline realism, and internal consistency.

**Cybersecurity Reasoning:** The system presents all 12 technical investigation results and content analysis findings to Gemma 4 with a cybersecurity analyst persona prompt. The model produces a structured JSON response with a risk score, verdict, red flags list, green flags list, and a detailed explanation — all grounded in the technical evidence.

**Domain Discovery:** When no website is found in the job posting, Gemma 4 attempts to infer the company's domain from the company name, enabling automated investigation even for postings that only provide an email address.

> **Why Gemma 4 matters here:** Unlike rule-based systems, Gemma 4 understands context, nuance, and sarcasm in job postings. It can identify that "Congratulations! You have been selected" without any interview process is a red flag, or that requesting bank details via email is abnormal. The 31B parameter model provides the reasoning depth needed to weigh contradictory signals.

---

## How It Works (Pipeline)

```
Upload (text paste or image)
        |
        v
   OCR Extraction (Tesseract)
        |
        v
   Entity Extraction (Gemma 4 LLM + regex)
        |
        v
   Technical Investigation
   ├── WHOIS / RDAP
   ├── DNS (A, MX, TXT, SPF, DMARC)
   ├── SSL Certificate
   ├── HTTP Headers & Status
   ├── robots.txt / sitemap.xml
   ├── Email Domain Validation (Abstract API)
   ├── Phone Validation (Abstract API)
   └── Live Website Verification
        |
        v
   Content Analysis (Gemma 4 LLM)
        |
        v
   AI Reasoning (Gemma 4 — cybersecurity analyst persona)
        |
        v
   Combined Risk Score
   ├── Technical Risk   (35%)
   ├── Content Risk     (30%)
   └── Reasoning Risk   (35%)
        |
        v
   Verdict: SAFE / SUSPICIOUS / SCAM
```

---

## 12 Technical Checks

| # | Check | Weight |
|---|-------|--------|
| 1 | Domain Registered | High |
| 2 | Website Reachable | Medium |
| 3 | HTTPS Enabled | High |
| 4 | SSL Certificate Valid | High |
| 5 | MX Record | Medium |
| 6 | SPF Record | Medium |
| 7 | DMARC Record | Medium |
| 8 | Email Domain Match | High |
| 9 | Disposable Email | High |
| 10 | Free Email Provider | Low |
| 11 | Live Website Verification | Medium |
| 12 | Phone Valid | Medium |

---

## Challenges Faced

**SSE Streaming Debugging:** Progress events were not reaching the browser because synchronous blocking calls (OCR, LLM HTTP requests, DNS lookups) were starving the uvicorn event loop. The fix required wrapping every blocking call in `asyncio.to_thread()` and adding `await asyncio.sleep()` after every yield to flush the socket buffer. This was the hardest bug to diagnose.

**Entity Extraction Accuracy:** Early versions struggled with malformed job postings — missing separators, inconsistent formatting, non-standard email formats. We added a regex-based fallback that runs in parallel with Gemma 4 extraction and merges results.

**Multi-Stage Risk Scoring:** Balancing technical vs. content vs. reasoning signals required careful weight tuning. A domain with valid WHOIS but scam content should still score high risk. The 35/30/35 split was determined through iterative testing.

**API Key Management:** Multiple API keys (OpenRouter, Abstract API) needed secure management. We implemented a full `.env`-based configuration layer with startup validation — no secrets in source code or frontend.

---

## Project Structure

```
gemma4-ai-project_2026/
├── backend/
│   ├── main.py              # FastAPI app, SSE streaming endpoint
│   ├── config.py            # Environment variable loader
│   ├── llm_client.py        # OpenRouter LLM client
│   ├── ocr.py               # Tesseract OCR wrapper
│   ├── entities.py          # Entity extraction (Gemma 4 + regex)
│   ├── investigation.py     # Technical checks (WHOIS, DNS, SSL, etc.)
│   ├── analysis.py          # Content analysis via Gemma 4
│   ├── reasoning.py         # AI reasoning prompt + parser
│   ├── abstract_api.py      # Abstract API client (email/phone/IP)
│   ├── models.py            # Pydantic data models
│   └── requirements.txt     # Python dependencies
├── dashboard/
│   ├── dashboard.html       # Dashboard UI
│   ├── dashboard.js         # SSE streaming, result rendering
│   └── dashboard.css        # Styling
├── auth/                    # Login/signup pages
├── navbar/                  # Navigation pages (features, how-it-works, etc.)
├── assets/                  # Landing page images
├── render/
│   ├── Dockerfile           # Docker build for Render deployment
│   └── .dockerignore        # Docker build exclusions
├── index.html               # Landing page
├── .env.example             # Environment variable template
├── .gitignore
├── LICENSE
└── README.md
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/analyze` | Analyze a job posting (returns JSON) |
| POST | `/api/analyze-stream` | Analyze with SSE streaming progress events |
| GET | `/api/health` | Health check + LLM status |
| GET | `/dashboard` | Dashboard UI |
| GET | `/` | Landing page |

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `OPENROUTER_MODEL` | No | Default: `google/gemma-4-31b-it` |
| `OPENROUTER_BASE_URL` | No | Default: `https://openrouter.ai/api/v1` |
| `ABSTRACT_EMAIL_API_KEY` | No | Email validation API key |
| `ABSTRACT_PHONE_API_KEY` | No | Phone intelligence API key |
| `ABSTRACT_IP_API_KEY` | No | IP geolocation API key |

---

## Future Scope

- Browser extension for auto-analyzing job listings on LinkedIn, Indeed, and Glassdoor
- Batch analysis mode for recruiting agencies
- Community-sourced scam database for cross-referencing
- Multi-language support for international job markets
- Real-time notification system for previously safe postings later flagged as scam

---

## Authors

- **Roshan Mallick** — [GitHub](https://github.com/Roshan-Mallick)
- **Om Srivastava** — [GitHub](https://github.com/Om-Srivastava-6)
- **Aditya Mishra** — [GitHub](https://github.com/AdityaMishra2007-codes)

---

## License

MIT License
