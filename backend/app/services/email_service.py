"""Brevo (Sendinblue) Transactional Email Service.

Uses Brevo's REST API v3 to send free transactional emails (300/day):
- Password reset verification OTPs
- Classroom security & phone usage alerts
"""

import asyncio
import logging
import os
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Brevo API Key
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()

# Verified Brevo Sender
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "yashureddy155@gmail.com").strip()
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Classpulse: Classroom Monitoring System").strip()

BREVO_SMTP_URL = "https://api.brevo.com/v3/smtp/email"


async def send_brevo_email(
    to_email: str,
    subject: str,
    html_content: str,
    recipient_name: str = "User",
    text_content: Optional[str] = None
) -> dict:
    """Send a transactional email using Brevo's REST API v3."""
    api_key = BREVO_API_KEY or os.environ.get("BREVO_API_KEY", "").strip()
    if not api_key:
        logger.error("Brevo API key not configured for email dispatch.")
        return {"status": "error", "error": "Brevo API key not configured"}

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    payload = {
        "sender": {
            "name": BREVO_SENDER_NAME,
            "email": BREVO_SENDER_EMAIL,
        },
        "to": [
            {
                "email": to_email.strip(),
                "name": recipient_name or "User",
            }
        ],
        "subject": subject,
        "htmlContent": html_content,
    }
    if text_content:
        payload["textContent"] = text_content

    try:
        logger.info(f"Dispatching transactional email via Brevo to {to_email} ('{subject}')...")
        resp = await asyncio.to_thread(requests.post, BREVO_SMTP_URL, json=payload, headers=headers, timeout=12)
        logger.info(f"Brevo email HTTP response: {resp.status_code}, {resp.text[:250]}")

        if resp.status_code in (200, 201):
            data = resp.json() if resp.text else {}
            msg_id = data.get("messageId") or "OK"
            return {
                "status": "sent",
                "provider": "Brevo (Transactional Email)",
                "to": to_email,
                "message_id": msg_id,
            }

        # Error response
        err_msg = f"HTTP {resp.status_code}"
        try:
            err_data = resp.json()
            err_msg = err_data.get("message") or err_data.get("detail") or err_msg
        except Exception:
            if resp.text:
                err_msg = resp.text[:200]

        return {
            "status": "error",
            "provider": "Brevo (Transactional Email)",
            "to": to_email,
            "error": err_msg,
        }
    except Exception as e:
        logger.error(f"Brevo email dispatch exception: {e}")
        return {
            "status": "error",
            "provider": "Brevo (Transactional Email)",
            "to": to_email,
            "error": str(e),
        }


async def send_otp_email(to_email: str, otp_code: str, recipient_name: str = "Teacher") -> dict:
    """Send a secure 6-digit OTP verification email for password reset."""
    subject = f"Classpulse Verification Code: {otp_code}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Classpulse Verification Code</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 24px; color: #1e293b; }}
        .card {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .logo {{ font-size: 20px; font-weight: 800; color: #4f46e5; margin-bottom: 24px; display: inline-block; }}
        .header {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }}
        .subtitle {{ font-size: 14px; color: #64748b; margin-bottom: 24px; line-height: 1.5; }}
        .otp-box {{ background: #f8fafc; border: 2px dashed #6366f1; border-radius: 10px; padding: 18px; text-align: center; margin: 24px 0; }}
        .otp-code {{ font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #4338ca; }}
        .expiry {{ font-size: 12px; color: #ef4444; font-weight: 600; margin-top: 8px; }}
        .footer {{ font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; line-height: 1.4; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="logo">🎓 Classpulse Monitoring</div>
        <div class="header">Password Reset Verification</div>
        <div class="subtitle">Hello {recipient_name},<br>You requested to reset your password for the Classroom Monitoring portal. Use the 6-digit verification code below:</div>
        
        <div class="otp-box">
          <div class="otp-code">{otp_code}</div>
          <div class="expiry">⏱ Valid for 10 minutes only</div>
        </div>
        
        <p style="font-size: 13px; color: #475569; line-height: 1.5;">
          If you did not request this verification code, please ignore this email or notify your system administrator immediately.
        </p>
        
        <div class="footer">
          Classpulse Classroom Monitoring & Anomaly Detection System<br>
          Automated transactional email powered by Brevo API.
        </div>
      </div>
    </body>
    </html>
    """

    text = f"Classpulse: Your password reset verification code is {otp_code}. Valid for 10 minutes."
    return await send_brevo_email(to_email, subject, html, recipient_name, text)


async def send_alert_email(to_email: str, alert_data: dict, student_info: Optional[dict] = None) -> dict:
    """Send a detailed classroom security incident notification via Brevo email."""
    stu_name = alert_data.get("student_name") or (student_info and student_info.get("name")) or "Student"
    roll_num = alert_data.get("roll_number") or (student_info and student_info.get("roll_number")) or "N/A"
    dept = alert_data.get("department") or (student_info and student_info.get("department")) or "Computer Science"
    sec = alert_data.get("section") or (student_info and student_info.get("section")) or ""
    duration = alert_data.get("duration", 0)
    context = alert_data.get("context", "LECTURE")
    evidence_url = alert_data.get("evidence_url", "")
    full_evidence = evidence_url if evidence_url.startswith("http") else f"http://localhost:8000{evidence_url}"

    subject = f"⚠️ Classroom Phone Alert: {stu_name} ({roll_num})"
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Classroom Phone Usage Alert</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b; }}
        .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .badge {{ display: inline-block; padding: 4px 10px; background: #fef2f2; color: #dc2626; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; margin-bottom: 16px; border: 1px solid #fee2e2; }}
        .title {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 12px; }}
        .details {{ background: #f8fafc; border-radius: 8px; padding: 16px; margin: 16px 0; border: 1px solid #e2e8f0; font-size: 13px; line-height: 1.8; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #4f46e5; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 13px; margin-top: 12px; }}
        .footer {{ font-size: 11px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <span class="badge">⚠️ Security & Discipline Alert</span>
        <div class="title">Unauthorized Phone Usage Detected</div>
        <p style="font-size: 13px; color: #475569; line-height: 1.6;">
          Our AI classroom monitoring system detected mobile phone activity during an academic session.
        </p>
        <div class="details">
          <strong>Student Name:</strong> {stu_name}<br>
          <strong>Roll Number:</strong> {roll_num}<br>
          <strong>Department:</strong> {dept}{f' - Sec {sec}' if sec else ''}<br>
          <strong>Context:</strong> {context}<br>
          <strong>Duration:</strong> {duration:.1f}s<br>
        </div>
        <a href="{full_evidence}" class="btn" target="_blank">▶ Watch Recorded Evidence Clip</a>
        <div class="footer">
          Classpulse Monitoring System • Automated notification powered by Brevo API
        </div>
      </div>
    </body>
    </html>
    """
    return await send_brevo_email(to_email, subject, html, stu_name)
