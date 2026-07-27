import socket
import smtplib
import logging
import traceback
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel, Field

from .config import FEEDBACK_EMAIL, FEEDBACK_EMAIL_PASSWORD, FEEDBACK_RECIPIENTS

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 20


def _resolve_ipv4(host: str) -> str:
    """Resolve hostname to an IPv4 address to avoid IPv6 on IPv4-only networks."""
    try:
        addr_info = socket.getaddrinfo(host, SMTP_PORT, socket.AF_INET, socket.SOCK_STREAM)
        ipv4 = addr_info[0][4][0]
        logger.info(f"SMTP: resolved {host} -> {ipv4} (IPv4)")
        return ipv4
    except socket.gaierror as e:
        logger.warning(f"SMTP: IPv4 resolution failed for {host}: {e} — falling back to hostname")
        return host


class FeedbackRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=200)
    category: str = Field(..., min_length=1, max_length=50)
    rating: int = Field(..., ge=1, le=5)
    message: str = Field(..., min_length=10, max_length=2000)


def _build_email_html(data: FeedbackRequest, timestamp: str) -> str:
    stars = "★" * data.rating + "☆" * (5 - data.rating)
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f4f6f9;">
      <div style="max-width:600px;margin:30px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <div style="background:linear-gradient(135deg,#225BE3,#1A46B8);padding:28px 32px;color:#fff;">
          <h1 style="margin:0;font-size:22px;font-weight:700;">SafeHire AI — New Feedback</h1>
          <p style="margin:6px 0 0;font-size:13px;opacity:0.85;">Submitted via the feedback form</p>
        </div>
        <div style="padding:28px 32px;">
          <table style="width:100%;border-collapse:collapse;font-size:14px;color:#374151;">
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;width:120px;">Name</td>
              <td style="padding:10px 0;">{data.name}</td>
            </tr>
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;">Email</td>
              <td style="padding:10px 0;"><a href="mailto:{data.email}" style="color:#225BE3;">{data.email}</a></td>
            </tr>
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;">Category</td>
              <td style="padding:10px 0;">{data.category}</td>
            </tr>
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;">Rating</td>
              <td style="padding:10px 0;font-size:18px;color:#F59E0B;">{stars} <span style="font-size:13px;color:#6B7280;">({data.rating}/5)</span></td>
            </tr>
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;vertical-align:top;">Message</td>
              <td style="padding:10px 0;line-height:1.6;">{data.message.replace(chr(10), '<br>')}</td>
            </tr>
            <tr>
              <td style="padding:10px 0;font-weight:600;color:#6B7280;">Submitted</td>
              <td style="padding:10px 0;color:#9CA3AF;">{timestamp}</td>
            </tr>
          </table>
        </div>
        <div style="padding:16px 32px;background:#f9fafb;border-top:1px solid #E5E7EB;font-size:12px;color:#9CA3AF;text-align:center;">
          SafeHire AI — Job Post Verification System &middot; Build with Gemma Hackathon 2026
        </div>
      </div>
    </body>
    </html>
    """


def send_feedback_email(data: FeedbackRequest) -> bool:
    logger.info(f"SMTP: host={SMTP_HOST} port={SMTP_PORT} encryption=STARTTLS timeout={SMTP_TIMEOUT}s")
    logger.info(f"SMTP: EMAIL configured={'yes' if FEEDBACK_EMAIL else 'no'}, EMAIL_PASSWORD configured={'yes' if FEEDBACK_EMAIL_PASSWORD else 'no'}")

    if not FEEDBACK_EMAIL or not FEEDBACK_EMAIL_PASSWORD:
        logger.warning("Feedback email not configured — set EMAIL and EMAIL_PASSWORD in Render environment")
        return False

    if not FEEDBACK_RECIPIENTS:
        logger.warning("No feedback recipients configured")
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    html_content = _build_email_html(data, timestamp)
    plain_text = (
        f"New feedback from {data.name} ({data.email})\n"
        f"Category: {data.category}\n"
        f"Rating: {data.rating}/5\n"
        f"Submitted: {timestamp}\n\n"
        f"{data.message}"
    )

    smtp_addr = _resolve_ipv4(SMTP_HOST)
    sent_count = 0
    try:
        logger.info(f"SMTP: connecting to {smtp_addr}:{SMTP_PORT} (timeout={SMTP_TIMEOUT}s) ...")
        server = smtplib.SMTP(smtp_addr, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        logger.info(f"SMTP: EHLO done, upgrading to STARTTLS ...")
        server.starttls()
        server.ehlo()
        logger.info(f"SMTP: STARTTLS done, authenticating as {FEEDBACK_EMAIL} ...")
        server.login(FEEDBACK_EMAIL, FEEDBACK_EMAIL_PASSWORD)
        logger.info(f"SMTP: authentication successful")

        for recipient in FEEDBACK_RECIPIENTS:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[SafeHire Feedback] {data.category} — {data.name}"
                msg["From"] = f"SafeHire AI Feedback <{FEEDBACK_EMAIL}>"
                msg["To"] = recipient
                msg["Reply-To"] = data.email
                msg.attach(MIMEText(plain_text, "plain"))
                msg.attach(MIMEText(html_content, "html"))
                server.sendmail(FEEDBACK_EMAIL, recipient, msg.as_string())
                sent_count += 1
                logger.info(f"Feedback email delivered to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send to {recipient}: {e}\n{traceback.format_exc()}")

        server.quit()
        logger.info(f"SMTP: connection closed")

        if sent_count > 0:
            logger.info(f"Feedback from {data.email} delivered to {sent_count}/{len(FEEDBACK_RECIPIENTS)} recipient(s)")
            return True
        else:
            logger.error("Failed to deliver feedback to any recipient")
            return False

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}\n{traceback.format_exc()}")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"Could not connect to SMTP server: {e}\n{traceback.format_exc()}")
        return False
    except socket.timeout as e:
        logger.error(f"SMTP connection timed out after {SMTP_TIMEOUT}s: {e}\n{traceback.format_exc()}")
        return False
    except socket.gaierror as e:
        logger.error(f"SMTP DNS resolution failed: {e}\n{traceback.format_exc()}")
        return False
    except OSError as e:
        logger.error(f"SMTP network error (errno={e.errno}): {e}\n{traceback.format_exc()}")
        return False
    except Exception as e:
        logger.error(f"Feedback email delivery failed: {e}\n{traceback.format_exc()}")
        return False
