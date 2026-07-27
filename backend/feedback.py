import smtplib
import logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel, Field

from .config import FEEDBACK_EMAIL, FEEDBACK_EMAIL_PASSWORD, FEEDBACK_RECIPIENTS

logger = logging.getLogger(__name__)


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

    sent_count = 0
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(FEEDBACK_EMAIL, FEEDBACK_EMAIL_PASSWORD)

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
                    logger.error(f"Failed to send to {recipient}: {e}")

        if sent_count > 0:
            logger.info(f"Feedback from {data.email} delivered to {sent_count}/{len(FEEDBACK_RECIPIENTS)} recipient(s)")
            return True
        else:
            logger.error("Failed to deliver feedback to any recipient")
            return False

    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail SMTP authentication failed — check EMAIL and EMAIL_PASSWORD (use a Gmail App Password)")
        return False
    except smtplib.SMTPConnectError:
        logger.error("Could not connect to Gmail SMTP server")
        return False
    except Exception as e:
        logger.error(f"Feedback email delivery failed: {e}")
        return False
