"""Settings API endpoints — context mode, model info, configuration, and Free/Carrier Notification Gateways."""

import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from backend.app.services.sms_service import get_sms_config, save_sms_config, send_sms

logger = logging.getLogger(__name__)
router = APIRouter()


class ContextUpdate(BaseModel):
    mode: str  # LECTURE, EXAM, BREAK, AUTHORIZED_PHONE_ACTIVITY


class SMSConfigUpdate(BaseModel):
    provider: str = "smsmode"  # "smsmode", "callmebot", "telegram", "android_sim", "textbee", "fast2sms", "twilio", "none"
    # smsmode (Free OTP SMS)
    smsmode_api_key: Optional[str] = ""
    smsmode_sender_id: Optional[str] = ""
    # 100% Free Channels
    callmebot_api_key: Optional[str] = ""
    callmebot_phone: Optional[str] = "916363661265"
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    android_gateway_url: Optional[str] = ""
    android_gateway_user: Optional[str] = ""
    android_gateway_password: Optional[str] = ""
    textbee_api_key: Optional[str] = ""
    textbee_device_id: Optional[str] = ""
    # Carrier Gateways
    fast2sms_api_key: Optional[str] = ""
    twilio_account_sid: Optional[str] = ""
    twilio_auth_token: Optional[str] = ""
    twilio_from_number: Optional[str] = ""


class SMSTestRequest(BaseModel):
    mobile_number: str = "6363661265"
    message: Optional[str] = None


@router.get("/settings/context")
async def get_context(request: Request):
    """Get current classroom context."""
    service = request.app.state.inference_service
    ctx = service.pipeline.context_engine
    return {
        "mode": ctx.current_mode_str,
        "multiplier": ctx.get_context().multiplier,
    }


@router.post("/settings/context")
async def set_context(request: Request, body: ContextUpdate):
    """Change classroom context mode."""
    service = request.app.state.inference_service
    success = service.set_context(body.mode)
    if not success:
        raise HTTPException(400, f"Invalid context mode: {body.mode}")
    return {"mode": body.mode}


@router.get("/settings/model-info")
async def get_model_info(request: Request):
    """Get AI model information."""
    service = request.app.state.inference_service
    return service.pipeline.detector.get_model_info()


@router.get("/settings/sms")
async def get_sms_settings():
    """Get current notification gateway settings with masked keys."""
    cfg = await get_sms_config()
    provider = cfg.get("provider", "smsmode")
    smsmode_key = cfg.get("smsmode_api_key", "")
    smsmode_sender = cfg.get("smsmode_sender_id", "")
    callmebot_key = cfg.get("callmebot_api_key", "")
    telegram_token = cfg.get("telegram_bot_token", "")
    fast2sms_key = cfg.get("fast2sms_api_key", "")
    twilio_token = cfg.get("twilio_auth_token", "")

    # Mask secrets
    masked_callmebot = (callmebot_key[:2] + "••••" + callmebot_key[-2:]) if len(callmebot_key) > 4 else ("Configured" if callmebot_key else "")
    masked_telegram = (telegram_token[:6] + "••••••••" + telegram_token[-4:]) if len(telegram_token) > 10 else ("Configured" if telegram_token else "")
    masked_fast2sms = (fast2sms_key[:4] + "••••••••" + fast2sms_key[-3:]) if len(fast2sms_key) > 8 else ("Configured" if fast2sms_key else "")
    masked_twilio_token = "••••••••" if twilio_token else ""

    textbee_key = cfg.get("textbee_api_key", "")
    textbee_device = cfg.get("textbee_device_id", "")

    is_configured = bool(
        smsmode_key
        or callmebot_key
        or (telegram_token and cfg.get("telegram_chat_id"))
        or cfg.get("android_gateway_url")
        or (textbee_key and textbee_device)
        or fast2sms_key
        or (cfg.get("twilio_account_sid") and twilio_token)
    )

    return {
        "provider": provider,
        "is_configured": is_configured,
        "has_smsmode_key": bool(smsmode_key),
        "smsmode_api_key": "",
        "smsmode_sender_id": smsmode_sender,
        "has_callmebot_key": bool(callmebot_key),
        "callmebot_api_key": "",
        "callmebot_phone": cfg.get("callmebot_phone", "916363661265"),
        "has_telegram_token": bool(telegram_token),
        "telegram_bot_token": "",
        "telegram_chat_id": cfg.get("telegram_chat_id", ""),
        "android_gateway_url": cfg.get("android_gateway_url", ""),
        "android_gateway_user": cfg.get("android_gateway_user", ""),
        "has_android_gateway_password": bool(cfg.get("android_gateway_password", "")),
        "android_gateway_password": "",
        "has_textbee_key": bool(textbee_key),
        "textbee_api_key": "",
        "textbee_device_id": textbee_device,
        "has_fast2sms_key": bool(fast2sms_key),
        "fast2sms_api_key": "",
        "twilio_account_sid": cfg.get("twilio_account_sid", ""),
        "has_twilio_token": bool(twilio_token),
        "twilio_auth_token": "",
        "twilio_from_number": cfg.get("twilio_from_number", ""),
    }


@router.post("/settings/sms")
async def update_sms_settings(body: SMSConfigUpdate):
    """Save updated notification gateway configuration."""
    clean = await save_sms_config(body.dict())
    return {"success": True, "provider": clean.get("provider"), "message": "Notification gateway settings saved successfully."}


@router.post("/settings/sms/test")
async def test_sms_delivery(body: SMSTestRequest):
    """Send an immediate test alert to verify notification delivery."""
    number = body.mobile_number.strip()
    if not number:
        raise HTTPException(400, "Mobile number required")

    msg = body.message or (
        "Classroom Monitoring System: Alert notification test. "
        "If you received this message, mobile alerts are working properly without cost!"
    )

    result = await send_sms(number, msg)
    return {
        "success": result.get("status") in ("sent", "logged"),
        "status": result.get("status"),
        "provider": result.get("provider"),
        "details": result,
    }
