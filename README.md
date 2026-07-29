# SafeHire AI

### AI-Powered Job Scam Detection Platform Built with Gemma 4

**Selected Theme:** Protecting People Online\
**Build with Gemma Hackathon 2026**

------------------------------------------------------------------------

# 🌐 Live Deployment

  -------------------------------------------------------------------------------------------------------------
  Component                      Platform                    URL
  ------------------------------ --------------------------- --------------------------------------------------
  **Frontend (UI)**              Vercel                      https://safehire-ai.vercel.app

  **Backend (API)**              Render (Docker)             https://gemma4-ai-project-2026-azb0.onrender.com

  -------------------------------------------------------------------------------------------------------------

### Pipeline Visualization

Explore the complete architecture and workflow:

**https://safehire-ai-pipeline.netlify.app/**

The visualization covers:

-   User Input
-   OCR Extraction
-   Entity Extraction (Gemma 4)
-   Technical Investigation
-   WHOIS
-   DNS (MX/SPF/DMARC)
-   SSL Validation
-   Website Reachability
-   Email Validation
-   Phone Validation
-   VirusTotal URL Reputation
-   Content Analysis
-   AI Cybersecurity Reasoning
-   Weighted Risk Scoring
-   Final Dashboard

------------------------------------------------------------------------

# Why SafeHire AI

SafeHire AI is an AI-powered cybersecurity platform that detects
fraudulent job postings by combining deep technical investigation with
large language model reasoning.

### Key Highlights

-   12 independent cybersecurity checks
-   Gemma 4 integrated into multiple pipeline stages
-   OCR support for screenshot uploads
-   VirusTotal URL reputation analysis
-   Real-time Server-Sent Events (SSE)
-   Explainable AI reasoning
-   Weighted multi-stage risk scoring

------------------------------------------------------------------------

# Problem Statement

Job scams continue to cause significant financial losses and identity
theft worldwide. Existing spam filters mainly analyze email content but
often ignore technical indicators such as domain registration, DNS
configuration, SSL certificates, and reputation.

SafeHire AI addresses this by combining cybersecurity investigation with
AI reasoning to produce evidence-based verdicts.

------------------------------------------------------------------------

# Solution Workflow

1.  User pastes a job description or uploads a screenshot.
2.  OCR extracts text (for images).
3.  Gemma 4 extracts entities.
4.  Technical investigation performs security checks.
5.  VirusTotal provides URL reputation.
6.  Gemma 4 analyzes content.
7.  AI combines all evidence.
8.  Weighted scoring produces a final verdict.

------------------------------------------------------------------------

# Technical Investigation

-   WHOIS Registration
-   DNS Records (A, MX, SPF, DMARC)
-   SSL Certificate Validation
-   Website Reachability
-   HTTP Header Inspection
-   Email Validation
-   Phone Validation
-   VirusTotal URL Reputation

------------------------------------------------------------------------

# AI Pipeline

    User Input
          │
          ▼
    OCR
          │
          ▼
    Entity Extraction (Gemma 4)
          │
          ▼
    Technical Investigation
          │
          ├── WHOIS
          ├── DNS
          ├── SSL
          ├── Email Validation
          ├── Phone Validation
          └── VirusTotal
          │
          ▼
    Content Analysis
          │
          ▼
    AI Cybersecurity Reasoning
          │
          ▼
    Weighted Risk Score
          │
          ▼
    SAFE / SUSPICIOUS / SCAM

------------------------------------------------------------------------

# Technology Stack

-   Python 3.12
-   FastAPI
-   Uvicorn
-   Gemma 4 (OpenRouter)
-   Tesseract OCR
-   Abstract API
-   VirusTotal API
-   Docker
-   Render
-   Vercel
-   Netlify

------------------------------------------------------------------------

# API Endpoints

  Method   Endpoint                Description
  -------- ----------------------- --------------------------
  POST     `/api/analyze`          Analyze job posting
  POST     `/api/analyze-stream`   Stream analysis progress
  GET      `/api/health`           Health endpoint

------------------------------------------------------------------------

# Future Enhancements

-   Browser Extension
-   Batch Analysis
-   Scam Intelligence Database
-   Multi-language Support
-   Historical Threat Monitoring

------------------------------------------------------------------------

# Authors

-   Roshan Mallick
-   Om Srivastava
-   Aditya Mishra

------------------------------------------------------------------------

# License

MIT License
