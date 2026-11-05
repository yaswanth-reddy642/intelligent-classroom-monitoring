"""SMS & Mobile Notification Service — Free & Carrier Options.

Supports multiple delivery channels:
1. CallMeBot WhatsApp (100% Free Forever — no credit card, no telecom fee)
   - Dispatches instant WhatsApp notifications directly to the student/parent phone (e.g. 6363661265).
2. Telegram Bot API (100% Free Forever — unlimited messages and video clips)
   - Delivers instant notifications with audio ping and playable video evidence clip.
3. Android Local SIM Gateway (100% Free Cellular SMS)
   - Uses your own Android phone's daily 100 free SMS (Jio/Airtel/Vi) via a local open-source gateway app.
4. Fast2SMS (Indian Gateway — includes ₹50 free testing credits upon registration)
   - Direct cellular route to Indian numbers (+91).
5. Twilio (Global Gateway — includes $15.50 free trial credits)
   - International cellular route.
6. Simulation / Logged Mode
   - System logs when no credentials are configured.
"""

import asyncio
import logging
import os
import socket
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════
# BREVO (SENDINBLUE) SERVICE CONFIGURATION
# Brevo API Key is configured in code and environment here.
# Configure your Brevo API key here in the code or via BREVO_API_KEY env var
# Brevo sends transactional SMS & OTPs directly to mobile phone inboxes worldwide.
# ═════════════════════════════════════════════════════════════════
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SMS_SENDER = os.environ.get("BREVO_SMS_SENDER", "Classroom").strip()

# Default Environment Fallbacks
DEFAULT_SMSMODE_KEY = os.environ.get("SMSMODE_API_KEY", "")
DEFAULT_SMSMODE_SENDER = os.environ.get("SMSMODE_SENDER_ID", "")
DEFAULT_TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
DEFAULT_TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
DEFAULT_TWILIO_FROM = os.environ.get("TWILIO_FROM_NUMBER", "")
DEFAULT_FAST2SMS_KEY = os.environ.get("FAST2SMS_API_KEY", "")
DEFAULT_CALLMEBOT_KEY = os.environ.get("CALLMEBOT_API_KEY", "")
DEFAULT_CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE", "916363661265")
DEFAULT_TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEFAULT_TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DEFAULT_ANDROID_GW = os.environ.get("ANDROID_GATEWAY_URL", "")

BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")
INSTITUTION = os.environ.get("INSTITUTION_NAME", "Classroom Monitoring System")

_cached_config: Optional[dict] = None


async def get_sms_config() -> dict:
    """Retrieve current SMS/Notification configuration from MongoDB or environment."""
    global _cached_config
    try:
        from backend.app.database.mongodb import get_db
        db = get_db()
        if db is not None:
            doc = await db.settings.find_one({"key": "sms_config"})
            if doc:
                _cached_config = doc.get("value", {})
                # In-code or .env BREVO_API_KEY takes immediate precedence
                active_brevo_key = BREVO_API_KEY or os.environ.get("BREVO_API_KEY", "").strip()
                if active_brevo_key or not _cached_config.get("brevo_api_key"):
                    _cached_config["brevo_api_key"] = active_brevo_key or _cached_config.get("brevo_api_key", "")
                if BREVO_SMS_SENDER or not _cached_config.get("brevo_sender"):
                    _cached_config["brevo_sender"] = BREVO_SMS_SENDER or _cached_config.get("brevo_sender", "Classroom")
                return _cached_config
    except Exception as e:
        logger.debug(f"Could not load SMS config from DB: {e}")

    # Fallback default: Brevo is primary
    return {
        "provider": "brevo",
        "brevo_api_key": BREVO_API_KEY,
        "brevo_sender": BREVO_SMS_SENDER,
        "smsmode_api_key": DEFAULT_SMSMODE_KEY,
        "smsmode_sender_id": DEFAULT_SMSMODE_SENDER,
        "callmebot_api_key": DEFAULT_CALLMEBOT_KEY,
        "callmebot_phone": DEFAULT_CALLMEBOT_PHONE,
        "telegram_bot_token": DEFAULT_TELEGRAM_TOKEN,
        "telegram_chat_id": DEFAULT_TELEGRAM_CHAT_ID,
        "android_gateway_url": DEFAULT_ANDROID_GW,
        "android_gateway_user": "",
        "android_gateway_password": "",
        "textbee_api_key": "",
        "textbee_device_id": "",
        "fast2sms_api_key": DEFAULT_FAST2SMS_KEY,
        "twilio_account_sid": DEFAULT_TWILIO_SID,
        "twilio_auth_token": DEFAULT_TWILIO_TOKEN,
        "twilio_from_number": DEFAULT_TWILIO_FROM,
    }


async def save_sms_config(config_data: dict) -> dict:
    """Save notification gateway configuration to MongoDB."""
    global _cached_config
    from backend.app.database.mongodb import get_db
    db = get_db()
    if db is None:
        raise RuntimeError("Database connection not ready")

    existing = await get_sms_config()

    def resolve_key(field_name: str) -> str:
        val = str(config_data.get(field_name, "")).strip()
        if not val or "•" in val or "\ufffd" in val:
            return existing.get(field_name, "")
        return val

    clean_config = {
        "provider": config_data.get("provider", "brevo"),
        # Brevo (Sendinblue) Transactional SMS API
        "brevo_api_key": resolve_key("brevo_api_key") or BREVO_API_KEY,
        "brevo_sender": config_data.get("brevo_sender", "Classroom").strip() or existing.get("brevo_sender", BREVO_SMS_SENDER or "Classroom"),
        # smsmode (Free OTP SMS)
        "smsmode_api_key": resolve_key("smsmode_api_key"),
        "smsmode_sender_id": config_data.get("smsmode_sender_id", "").strip() or existing.get("smsmode_sender_id", ""),
        # 100% Free Channels
        "callmebot_api_key": resolve_key("callmebot_api_key"),
        "callmebot_phone": config_data.get("callmebot_phone", "916363661265").strip() or existing.get("callmebot_phone", "916363661265"),
        "telegram_bot_token": resolve_key("telegram_bot_token"),
        "telegram_chat_id": config_data.get("telegram_chat_id", "").strip() or existing.get("telegram_chat_id", ""),
        "android_gateway_url": config_data.get("android_gateway_url", "").strip() or existing.get("android_gateway_url", ""),
        "android_gateway_user": config_data.get("android_gateway_user", "").strip() or existing.get("android_gateway_user", ""),
        "android_gateway_password": resolve_key("android_gateway_password"),
        "textbee_api_key": resolve_key("textbee_api_key"),
        "textbee_device_id": config_data.get("textbee_device_id", "").strip() or existing.get("textbee_device_id", ""),
        # Carrier Gateways
        "fast2sms_api_key": resolve_key("fast2sms_api_key"),
        "twilio_account_sid": config_data.get("twilio_account_sid", "").strip() or existing.get("twilio_account_sid", ""),
        "twilio_auth_token": resolve_key("twilio_auth_token"),
        "twilio_from_number": config_data.get("twilio_from_number", "").strip() or existing.get("twilio_from_number", ""),
    }

    await db.settings.update_one(
        {"key": "sms_config"},
        {"$set": {"key": "sms_config", "value": clean_config, "updated_at": datetime.now()}},
        upsert=True,
    )
    _cached_config = clean_config
    logger.info(f"SMS/Notification config updated in MongoDB. Provider: {clean_config['provider']}")
    return clean_config


def _format_timestamp(ts) -> str:
    """Convert Unix timestamp to human-readable date and time."""
    try:
        if isinstance(ts, (int, float)) and ts > 0:
            dt = datetime.fromtimestamp(ts)
            return dt.strftime("%d-%b-%Y %I:%M:%S %p")
        return "N/A"
    except Exception:
        return "N/A"


def _format_duration(seconds) -> str:
    """Format duration in human-readable form."""
    try:
        s = float(seconds)
        if s < 60:
            return f"{s:.1f} seconds"
        minutes = int(s // 60)
        secs = int(s % 60)
        return f"{minutes}m {secs}s"
    except Exception:
        return "N/A"


def get_base_url() -> str:
    """Get the base URL for generating accessible evidence links."""
    env_url = os.environ.get("APP_BASE_URL")
    if env_url:
        return env_url.rstrip("/")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return f"http://{ip}:8000"
    except Exception:
        pass
    return "http://localhost:8000"


def _build_evidence_url(alert_data: dict) -> str:
    """Build full evidence clip URL from alert data."""
    evidence_url = alert_data.get("evidence_url", "")
    if not evidence_url:
        evidence_path = alert_data.get("evidence_path", "")
        if evidence_path:
            try:
                from backend.app.services.evidence_service import get_evidence_url
                evidence_url = get_evidence_url(evidence_path)
            except Exception:
                pass
    if evidence_url:
        base = get_base_url()
        if evidence_url.startswith("/"):
            return f"{base}{evidence_url}"
        return evidence_url
    return ""


def format_student_alert_message(alert_data: dict, student_info: dict = None) -> str:
    """Format an alert message for the STUDENT's mobile."""
    timestamp = alert_data.get("timestamp", 0)
    duration = alert_data.get("duration", 0)
    score = alert_data.get("anomaly_score", 0)
    phone_conf = alert_data.get("phone_confidence", 0)
    context = alert_data.get("context", "LECTURE")
    camera = alert_data.get("camera_id", "CAM-01")
    reasons = alert_data.get("reasons", [])
    alert_id = alert_data.get("alert_id", "N/A")
    evidence_url = _build_evidence_url(alert_data)

    stu_name = "Student"
    stu_roll = alert_data.get("roll_number") or alert_data.get("student_display_id", "N/A")
    stu_dept = alert_data.get("department", "")
    stu_sec = alert_data.get("section", "")
    if student_info:
        stu_name = student_info.get("name", stu_name)
        stu_roll = student_info.get("roll_number", stu_roll)
        stu_dept = student_info.get("department", stu_dept)
        stu_sec = student_info.get("section", stu_sec)
    elif alert_data.get("student_name") and alert_data.get("student_name") not in ("Unknown Person", "Unknown", "Student"):
        stu_name = alert_data["student_name"]

    msg = f"⚠️ {INSTITUTION}\n"
    msg += f"DISCIPLINE ALERT: MOBILE PHONE DETECTED\n"
    msg += f"-----------------------------------------\n"
    msg += f"Dear {stu_name},\n"
    msg += f"Unauthorized phone usage was detected during your classroom session.\n\n"
    msg += f"Student Details:\n"
    msg += f"- Name: {stu_name}\n"
    msg += f"- Roll Number: {stu_roll}\n"
    if stu_dept:
        msg += f"- Department: {stu_dept}\n"
    if stu_sec:
        msg += f"- Section: {stu_sec}\n"
    msg += f"\nIncident Details:\n"
    msg += f"- Date & Time: {_format_timestamp(timestamp)}\n"
    msg += f"- Usage Duration: {_format_duration(duration)}\n"
    msg += f"- Phone Confidence: {phone_conf:.0%}\n"
    msg += f"- Anomaly Score: {score:.0%}\n"
    msg += f"- Session Context: {context}\n"
    msg += f"- Camera ID: {camera}\n"
    msg += f"- Alert ID: {alert_id}\n"
    if reasons:
        msg += f"- Reason: {'; '.join(reasons)}\n"

    if evidence_url:
        msg += f"\nVideo Evidence Clip:\n{evidence_url}\n"
        msg += f"(Tap link above to play recorded clip on your mobile phone)\n"

    msg += f"\nPlease refrain from using mobile phones during academic sessions."
    msg += f"\n-- {INSTITUTION}"
    return msg


def format_parent_alert_message(alert_data: dict, student_info: dict = None) -> str:
    """Format an alert message for the PARENT's mobile."""
    timestamp = alert_data.get("timestamp", 0)
    duration = alert_data.get("duration", 0)
    score = alert_data.get("anomaly_score", 0)
    phone_conf = alert_data.get("phone_confidence", 0)
    context = alert_data.get("context", "LECTURE")
    camera = alert_data.get("camera_id", "CAM-01")
    reasons = alert_data.get("reasons", [])
    alert_id = alert_data.get("alert_id", "N/A")
    evidence_url = _build_evidence_url(alert_data)

    stu_name = "Your ward"
    stu_roll = alert_data.get("roll_number") or alert_data.get("student_display_id", "N/A")
    stu_dept = alert_data.get("department", "")
    stu_sec = alert_data.get("section", "")
    if student_info:
        stu_name = student_info.get("name", stu_name)
        stu_roll = student_info.get("roll_number", stu_roll)
        stu_dept = student_info.get("department", stu_dept)
        stu_sec = student_info.get("section", stu_sec)
    elif alert_data.get("student_name") and alert_data.get("student_name") not in ("Unknown Person", "Unknown", "Student"):
        stu_name = alert_data["student_name"]

    msg = f"⚠️ {INSTITUTION}\n"
    msg += f"PARENT NOTIFICATION: CLASSROOM PHONE USAGE\n"
    msg += f"-----------------------------------------\n"
    msg += f"Dear Parent/Guardian,\n"
    msg += f"Your ward {stu_name}"
    if stu_roll and stu_roll != "N/A":
        msg += f" (Roll: {stu_roll})"
    msg += f" was detected using a mobile phone during a {context.lower()} session.\n\n"
    msg += f"Student Details:\n"
    msg += f"- Student: {stu_name}\n"
    msg += f"- Roll Number: {stu_roll}\n"
    if stu_dept:
        msg += f"- Department: {stu_dept}\n"
    if stu_sec:
        msg += f"- Section: {stu_sec}\n"
    msg += f"\nIncident Details:\n"
    msg += f"- Date & Time: {_format_timestamp(timestamp)}\n"
    msg += f"- Duration: {_format_duration(duration)}\n"
    msg += f"- Detection Confidence: {phone_conf:.0%}\n"
    msg += f"- Session Context: {context}\n"
    msg += f"- Camera: {camera}\n"
    msg += f"- Alert ID: {alert_id}\n"
    if reasons:
        msg += f"- Reason: {'; '.join(reasons)}\n"

    if evidence_url:
        msg += f"\nVideo Evidence Clip:\n{evidence_url}\n"
        msg += f"(Tap link above to watch recorded evidence clip on your mobile phone)\n"

    msg += f"\nKindly counsel your ward regarding classroom discipline."
    msg += f"\n-- {INSTITUTION}"
    return msg


async def send_sms(to_number: str, message: str) -> dict:
    """Send an SMS or instant mobile notification using the selected channel.

    Supports:
    - smsmode: Free developer credits OTP / SMS delivery directly to mobile inbox
    - callmebot: 100% Free WhatsApp notification directly to mobile phone
    - telegram: 100% Free Telegram Bot notification
    - android_sim: 100% Free cellular SMS using personal Android phone's SIM
    - textbee: 100% Free Android Cloud Gateway (300 SMS/mo)
    - fast2sms: Direct Indian SMS carrier route (includes free signup credits)
    - twilio: Global carrier route (includes $15 free trial)
    """
    if not to_number:
        return {"status": "skipped", "reason": "no_number"}

    clean_digits = "".join(ch for ch in str(to_number) if ch.isdigit())
    if len(clean_digits) > 10 and clean_digits.startswith("91"):
        ten_digit = clean_digits[2:]
        full_intl = clean_digits
    else:
        ten_digit = clean_digits[-10:]
        full_intl = f"91{ten_digit}"

    cfg = await get_sms_config()
    provider = cfg.get("provider", "brevo")

    # ═════════════════════════════════════════════════════════════════
    # 0. PRIMARY: Brevo (Sendinblue) Transactional SMS API
    # ═════════════════════════════════════════════════════════════════
    if provider == "brevo" or (BREVO_API_KEY and provider in ("brevo", "smsmode", "none")):
        brevo_key = (BREVO_API_KEY or os.environ.get("BREVO_API_KEY", "") or cfg.get("brevo_api_key", "")).strip()
        if not brevo_key:
            return {
                "status": "error",
                "provider": "Brevo (Transactional SMS)",
                "to": ten_digit,
                "error": "Brevo API Key is not configured. Please paste your Brevo API key in backend/app/services/sms_service.py (BREVO_API_KEY) or set the BREVO_API_KEY environment variable.",
            }

        sender = (cfg.get("brevo_sender") or BREVO_SMS_SENDER or "Classroom").strip()[:11]
        intl_recipient = f"+91{ten_digit}" if len(ten_digit) == 10 else f"+{full_intl.lstrip('+')}"

        try:
            logger.info(f"Dispatching real transactional SMS via Brevo to {intl_recipient} (sender: {sender})...")
            url = "https://api.brevo.com/v3/transactionalSMS/sms"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": brevo_key,
            }
            payload = {
                "sender": sender,
                "recipient": intl_recipient,
                "content": message,
                "type": "transactional",
            }

            resp = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=10)
            logger.info(f"Brevo HTTP response: {resp.status_code}, {resp.text[:250]}")

            if resp.status_code in (200, 201):
                data = resp.json() if resp.text else {}
                msg_id = data.get("reference") or data.get("messageId") or "OK"
                return {
                    "status": "sent",
                    "provider": "Brevo (Transactional SMS)",
                    "to": ten_digit,
                    "intl_to": intl_recipient,
                    "message_id": msg_id,
                    "response": data,
                }

            # Handle Brevo error responses
            err_msg = f"HTTP {resp.status_code}"
            try:
                err_data = resp.json()
                if "message" in err_data:
                    err_msg = err_data["message"]
                elif "detail" in err_data:
                    err_msg = err_data["detail"]
            except Exception:
                if resp.text:
                    err_msg = resp.text[:200]

            if resp.status_code in (401, 403):
                err_msg = f"Invalid Brevo API Key ({err_msg}). Please verify your key at https://app.brevo.com/settings/keys/api."
            elif resp.status_code == 402 or "credit" in err_msg.lower():
                err_msg = f"Brevo SMS credits required ({err_msg}). Please check SMS credits in your Brevo account dashboard."
            elif "not yet activated" in err_msg.lower() or "activation" in err_msg.lower():
                err_msg = f"Brevo SMS account activation needed: {err_msg} (Go to https://app.brevo.com/transactional/sms to enable SMS on your Brevo account)."

            return {
                "status": "error",
                "provider": "Brevo (Transactional SMS)",
                "to": ten_digit,
                "error": err_msg,
            }
        except Exception as e:
            logger.error(f"Brevo SMS dispatch exception: {e}")
            return {
                "status": "error",
                "provider": "Brevo (Transactional SMS)",
                "to": ten_digit,
                "error": str(e),
            }

    # ═════════════════════════════════════════════════════════════════
    # 1. FREE OTP SMS: smsmode REST API v1 (Direct Mobile SMS Inbox)
    # ═════════════════════════════════════════════════════════════════
    if provider == "smsmode":
        smsmode_key = cfg.get("smsmode_api_key", "").strip()
        sender_id = cfg.get("smsmode_sender_id", "").strip()
        if not smsmode_key:
            return {
                "status": "error",
                "provider": "smsmode (Free OTP SMS)",
                "to": ten_digit,
                "error": "smsmode API Key is missing. Please sign up for free at https://www.smsmode.com, copy your API Key from Settings -> API Keys, and save it in Settings.",
            }

        intl_phone = full_intl if full_intl.startswith("91") else f"91{ten_digit}"
        try:
            logger.info(f"Dispatching real SMS OTP via smsmode REST API to {intl_phone}...")
            url = "https://rest.smsmode.com/sms/v1/messages"
            headers = {
                "X-Api-Key": smsmode_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "recipient": {"to": intl_phone},
                "body": {"text": message},
            }
            if sender_id:
                payload["sender"] = sender_id

            resp = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=12)
            logger.info(f"smsmode REST API response status: {resp.status_code}, body: {resp.text[:250]}")

            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw": resp.text}
                msg_id = data.get("id") or data.get("messageId") or data.get("smsId") or "OK"
                return {
                    "status": "sent",
                    "provider": "smsmode (Free OTP SMS)",
                    "to": ten_digit,
                    "intl_to": intl_phone,
                    "message_id": msg_id,
                    "response": data,
                }

            # If REST returned error, attempt fallback to HTTP 1.6 in case of legacy token
            alt_url = "https://api.smsmode.com/http/1.6/sendSMS.do"
            alt_params = {
                "accessToken": smsmode_key,
                "message": message,
                "numero": intl_phone,
            }
            if sender_id:
                alt_params["emetteur"] = sender_id

            try:
                alt_resp = await asyncio.to_thread(requests.get, alt_url, params=alt_params, timeout=8)
                alt_text = alt_resp.text.strip()
                logger.info(f"smsmode HTTP 1.6 response: {alt_resp.status_code}, {alt_text[:150]}")
                if alt_resp.status_code in (200, 201) and (alt_text.startswith("0") or "success" in alt_text.lower()):
                    return {
                        "status": "sent",
                        "provider": "smsmode (Free OTP SMS)",
                        "to": ten_digit,
                        "intl_to": intl_phone,
                        "response": alt_text,
                    }
            except Exception as alt_err:
                logger.debug(f"smsmode HTTP 1.6 fallback ignored: {alt_err}")

            # Parse error explanation
            err_msg = f"HTTP {resp.status_code}"
            try:
                err_data = resp.json()
                if "detail" in err_data:
                    err_msg = f"{err_data.get('message', '')} - {err_data.get('detail', '')}".strip(" -")
                elif "message" in err_data:
                    err_msg = err_data["message"]
            except Exception:
                if resp.text:
                    err_msg = resp.text[:200]

            if resp.status_code in (401, 403):
                err_msg = f"Invalid smsmode API Key ({err_msg}). Please copy your API key from smsmode dashboard -> Settings -> API Keys."
            elif resp.status_code == 400 and ("credit" in err_msg.lower() or "solde" in err_msg.lower()):
                err_msg = "smsmode test credits exhausted. Please check balance at https://ui.smsmode.com."

            return {
                "status": "error",
                "provider": "smsmode (Free OTP SMS)",
                "to": ten_digit,
                "error": err_msg,
            }
        except Exception as e:
            logger.error(f"smsmode dispatch exception: {e}")
            return {
                "status": "error",
                "provider": "smsmode (Free OTP SMS)",
                "to": ten_digit,
                "error": str(e),
            }

    # ═════════════════════════════════════════════════════════════════
    # 1. 100% FREE: CallMeBot WhatsApp Notification
    # ═════════════════════════════════════════════════════════════════
    if provider == "callmebot":
        callmebot_key = cfg.get("callmebot_api_key", "").strip()
        target_phone = cfg.get("callmebot_phone", "").strip() or full_intl
        if not target_phone.startswith("91") and len(target_phone) == 10:
            target_phone = f"91{target_phone}"

        if callmebot_key:
            try:
                logger.info(f"Dispatching 100% FREE WhatsApp alert via CallMeBot to {target_phone}...")
                encoded_text = urllib.parse.quote(message)
                url = f"https://api.callmebot.com/whatsapp.php?phone={target_phone}&text={encoded_text}&apikey={callmebot_key}"
                resp = await asyncio.to_thread(requests.get, url, timeout=15)
                resp_text = resp.text.strip()
                clean_lower = resp_text.lower()
                is_ok = ("success" in clean_lower or "message queued" in clean_lower or "whatsapp" in clean_lower) and ("error" not in clean_lower and "invalid" not in clean_lower)
                if is_ok:
                    logger.info(f"WhatsApp alert successfully sent to {target_phone} via CallMeBot!")
                    return {
                        "status": "sent",
                        "provider": "CallMeBot (Free WhatsApp)",
                        "to": target_phone,
                        "response": resp_text,
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "CallMeBot (Free WhatsApp)",
                        "to": target_phone,
                        "error": resp_text,
                    }
            except Exception as e:
                logger.error(f"CallMeBot WhatsApp dispatch error: {e}")
                return {"status": "error", "provider": "CallMeBot (Free WhatsApp)", "to": target_phone, "error": str(e)}
        else:
            logger.info("CallMeBot API key not configured yet.")

    # ═════════════════════════════════════════════════════════════════
    # 2. 100% FREE: Telegram Bot API
    # ═════════════════════════════════════════════════════════════════
    if provider == "telegram":
        bot_token = cfg.get("telegram_bot_token", "").strip()
        chat_id = cfg.get("telegram_chat_id", "").strip()
        if bot_token and chat_id:
            try:
                logger.info(f"Dispatching 100% FREE Telegram alert to chat {chat_id}...")
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "disable_web_page_preview": False,
                }
                resp = await asyncio.to_thread(requests.post, url, json=payload, timeout=12)
                data = resp.json()
                if data.get("ok"):
                    logger.info(f"Telegram alert successfully delivered to chat {chat_id}!")
                    return {
                        "status": "sent",
                        "provider": "Telegram Bot (100% Free)",
                        "chat_id": chat_id,
                        "to": to_number,
                    }
                else:
                    err_desc = data.get("description", "Telegram API error")
                    if "chat not found" in err_desc.lower():
                        err_desc = "Bad Request: chat not found. You must open your bot in Telegram and click the 'Start' button (send /start) first so Telegram permits the bot to message you!"
                    return {
                        "status": "error",
                        "provider": "Telegram Bot (100% Free)",
                        "error": err_desc,
                    }
            except Exception as e:
                return {"status": "error", "provider": "Telegram Bot (100% Free)", "error": str(e)}

    # ═════════════════════════════════════════════════════════════════
    # 3. 100% FREE: Local Android SIM SMS Gateway (Uses your phone's SIM)
    # ═════════════════════════════════════════════════════════════════
    if provider == "android_sim":
        gw_url = cfg.get("android_gateway_url", "").strip()
        gw_user = cfg.get("android_gateway_user", "").strip()
        gw_pass = cfg.get("android_gateway_password", "").strip()
        auth = (gw_user, gw_pass) if (gw_user or gw_pass) else None

        if not gw_url:
            return {"status": "error", "provider": "Android SIM Gateway", "error": "Gateway URL is empty. Please enter your Android Phone's IP URL (e.g. http://192.168.1.5:8080)."}

        try:
            logger.info(f"Dispatching FREE GSM SMS through local Android SIM gateway at {gw_url}...")
            # Universal payload compatible with Simple SMS Gateway, Capcom6, TextBee, Envoy (E.164 standard)
            payload = {
                "phone": f"+91{ten_digit}",
                "to": f"+91{ten_digit}",
                "number": f"+91{ten_digit}",
                "phoneNumbers": [f"+91{ten_digit}", ten_digit],
                "message": message,
                "text": message,
                "textMessage": {"text": message},
            }

            from urllib.parse import urlparse
            clean_base = gw_url.rstrip("/")
            parsed = urlparse(clean_base if "://" in clean_base else f"http://{clean_base}")
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            url_path = parsed.path.rstrip("/")

            # Fast 2-second connection pre-check to prevent long 15s browser timeouts
            try:
                probe_sock = socket.create_connection((host, port), timeout=2.0)
                probe_sock.close()
            except Exception as sock_err:
                logger.warning(f"Android SIM Gateway probe unreachable at {host}:{port} - {sock_err}")
                return {
                    "status": "error",
                    "provider": "Android SIM Gateway",
                    "to": ten_digit,
                    "error": (
                        f"Cannot connect to Android phone at {host}:{port}. "
                        f"Please check: "
                        f"1) Is your Android phone connected to the SAME Wi-Fi as your PC (or your PC connected to your phone's Hotspot)? "
                        f"2) In the SMS Gateway app on your phone, did you tap 'Start Server'? "
                        f"3) Check the IP address displayed on your phone's screen."
                    ),
                }

            # If user already typed a specific path (e.g. /send-sms or /message or /send)
            if url_path:
                endpoints_to_try = [clean_base]
            else:
                endpoints_to_try = [
                    f"{clean_base}/message",       # SMS Gateway (capcom6 / sms-gate.app standard)
                    f"{clean_base}/send",          # Simple SMS Gateway / Envoy
                    f"{clean_base}/send-sms",      # Universal gateway route
                    f"{clean_base}/sms",           # OpenSMS
                    clean_base,                    # Root POST
                ]

            last_resp = None
            last_err = None
            for ep in endpoints_to_try:
                try:
                    resp = await asyncio.to_thread(requests.post, ep, json=payload, auth=auth, timeout=4.0)
                    if resp.status_code in (200, 201, 202):
                        # Verify response is genuine gateway response, not a router captive portal / login HTML page
                        content_type = resp.headers.get("Content-Type", "").lower()
                        resp_preview = (resp.text or "")[:400].lower()
                        if "text/html" in content_type or "<!doctype html" in resp_preview or "<html" in resp_preview:
                            return {
                                "status": "error",
                                "provider": "Android SIM Gateway",
                                "to": ten_digit,
                                "error": (
                                    f"Target address '{ep}' returned a network/router login web page instead of an Android SMS Gateway. "
                                    f"'{host}' is your Wi-Fi network's router gateway, NOT your Android phone. "
                                    f"Please open the SMS Gateway app on your phone and copy the exact IP address shown on your phone's screen."
                                ),
                            }
                        return {
                            "status": "sent",
                            "provider": "Android SIM Gateway (100% Free Cellular)",
                            "to": ten_digit,
                            "endpoint": ep,
                            "response": resp.text[:200] if resp.text else "OK",
                        }
                    last_resp = resp
                except Exception as try_err:
                    last_err = try_err
                    continue

            if last_resp is not None:
                resp_text = (last_resp.text or "")
                if "permission" in resp_text.lower() or "failed to send" in resp_text.lower() or "10358" in resp_text:
                    err_msg = (
                        f"Android Phone Permission Denied: '{resp_text.strip()}'. "
                        f"Please open your Android Phone -> Settings -> Apps -> Simple SMS Gateway -> App Permissions, "
                        f"and grant 'SMS' permission (Allow)."
                    )
                else:
                    err_msg = f"HTTP {last_resp.status_code}: {resp_text[:250]}"
                return {
                    "status": "error",
                    "provider": "Android SIM Gateway",
                    "to": ten_digit,
                    "error": err_msg,
                }
            err_msg = str(last_err) if last_err else "Failed to reach phone gateway"
            return {
                "status": "error",
                "provider": "Android SIM Gateway",
                "to": ten_digit,
                "error": f"Cannot connect to {gw_url}. Make sure your Android phone and PC are connected to the SAME Wi-Fi network and the SMS Gateway app is actively running. ({err_msg})",
            }
        except Exception as e:
            return {"status": "error", "provider": "Android SIM Gateway", "to": ten_digit, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════
    # 4. 100% FREE: TextBee.dev Mobile Phone Gateway Cloud REST API
    #    Uses your Android Phone's SIM via Cloud WebSocket/FCM
    # ═════════════════════════════════════════════════════════════════
    if provider == "textbee":
        api_key = cfg.get("textbee_api_key", "").strip()
        device_id = cfg.get("textbee_device_id", "").strip()
        if not api_key or not device_id:
            return {
                "status": "error",
                "provider": "TextBee Mobile Gateway",
                "to": ten_digit,
                "error": "TextBee API Key or Device ID missing. Please configure them in Settings -> Notification Gateway -> TextBee.",
            }
        try:
            logger.info(f"Dispatching SMS via TextBee Cloud Mobile Gateway to {ten_digit}...")
            url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/sendSMS"
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "recipients": [f"+91{ten_digit}", ten_digit],
                "message": message,
            }
            resp = await asyncio.to_thread(requests.post, url, json=payload, headers=headers, timeout=12)
            data = resp.json() if resp.text and resp.text.startswith("{") else {}
            if resp.status_code in (200, 201) and (data.get("success") or data.get("status") == "success"):
                logger.info(f"TextBee SMS successfully queued/sent to {ten_digit}!")
                return {
                    "status": "sent",
                    "provider": "TextBee Mobile Gateway (100% Free)",
                    "to": ten_digit,
                    "response": data,
                }
            else:
                err_text = data.get("message") or resp.text[:200] or f"HTTP {resp.status_code}"
                return {
                    "status": "error",
                    "provider": "TextBee Mobile Gateway",
                    "to": ten_digit,
                    "error": err_text,
                }
        except Exception as e:
            return {"status": "error", "provider": "TextBee Mobile Gateway", "to": ten_digit, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════
    # 5. Fast2SMS (Indian Gateway — Free signup credits / Paid)
    # ═════════════════════════════════════════════════════════════════
    if provider == "fast2sms":
        fast2sms_key = cfg.get("fast2sms_api_key", "").strip()
        if fast2sms_key:
            try:
                import re
                logger.info(f"Attempting carrier SMS dispatch via Fast2SMS to {ten_digit}...")
                otp_match = re.search(r'\b\d{6}\b', message)
                if otp_match:
                    payload = {
                        "variables_values": otp_match.group(0),
                        "route": "otp",
                        "numbers": ten_digit,
                    }
                else:
                    payload = {
                        "route": "q",
                        "message": message,
                        "language": "english",
                        "flash": 0,
                        "numbers": ten_digit,
                    }
                headers = {
                    "authorization": fast2sms_key,
                    "Content-Type": "application/json",
                }
                resp = await asyncio.to_thread(
                    requests.post,
                    "https://www.fast2sms.com/dev/bulkV2",
                    json=payload,
                    headers=headers,
                    timeout=12,
                )
                data = resp.json()
                if data.get("return") is True or resp.status_code == 200:
                    return {
                        "status": "sent",
                        "provider": "Fast2SMS (India)",
                        "to": ten_digit,
                        "response": data,
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "Fast2SMS (India)",
                        "to": ten_digit,
                        "error": data.get("message", "Fast2SMS carrier error"),
                    }
            except Exception as e:
                return {"status": "error", "provider": "Fast2SMS (India)", "to": ten_digit, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════
    # 5. Twilio (Global Gateway — $15.50 Free Trial Credits)
    # ═════════════════════════════════════════════════════════════════
    if provider == "twilio":
        twilio_sid = cfg.get("twilio_account_sid", "").strip()
        twilio_token = cfg.get("twilio_auth_token", "").strip()
        twilio_from = cfg.get("twilio_from_number", "").strip()
        if twilio_sid and twilio_token and twilio_from:
            try:
                e164_number = "+91" + ten_digit if len(ten_digit) == 10 else f"+{clean_digits}"
                from twilio.rest import Client
                client = Client(twilio_sid, twilio_token)
                msg = await asyncio.to_thread(
                    client.messages.create,
                    body=message,
                    from_=twilio_from,
                    to=e164_number,
                )
                return {
                    "status": "sent",
                    "provider": "Twilio",
                    "sid": msg.sid,
                    "to": e164_number,
                }
            except Exception as e:
                return {"status": "error", "provider": "Twilio", "to": to_number, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════
    # 6. Fallback: Log Mode (Simulation)
    # ═════════════════════════════════════════════════════════════════
    logger.info(f"[SIMULATION ALERT LOG] Recipient: {to_number} (Indian: +91 {ten_digit})")
    logger.info(f"[CONTENT]:\n{message}")
    return {
        "status": "logged",
        "provider": "simulation",
        "to": to_number,
        "message": message,
        "note": "Alert logged. To receive free instant messages on your mobile without any cost, switch to CallMeBot (Free WhatsApp) or Telegram Bot in Settings.",
    }


async def send_alert_sms(
    alert_data: dict,
    mobile_number: str,
    student_info: dict = None,
    is_parent: bool = False,
) -> dict:
    """Send an alert notification to a student or parent mobile number."""
    if is_parent:
        message = format_parent_alert_message(alert_data, student_info=student_info)
    else:
        message = format_student_alert_message(alert_data, student_info=student_info)
    return await send_sms(mobile_number, message)
