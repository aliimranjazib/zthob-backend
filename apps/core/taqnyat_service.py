import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings

from .phone_format import format_phone_for_taqnyat

logger = logging.getLogger(__name__)

VERIFY_URL = "https://api.taqnyat.sa/verify.php"
SMS_URL = "https://api.taqnyat.sa/v1/messages"

# Taqnyat Verify API response codes (https://dev.taqnyat.sa/en/doc/verify/)
VERIFY_CODE_SENT = 5
VERIFY_ALREADY_SENT = 7
VERIFY_SEND_ATTEMPTS_EXCEEDED = 8
VERIFY_SUCCESS = 10
VERIFY_INCORRECT = 11
VERIFY_ATTEMPTS_EXHAUSTED = 12
VERIFY_ALREADY_ACTIVATED = 13
VERIFY_NUMBER_ALREADY_VERIFIED = 19


class TaqnyatVerifyService:
    """Taqnyat Verify API for managed OTP send and check."""

    @staticmethod
    def _is_configured() -> tuple[bool, str]:
        if not settings.TAQNYAT_BEARER_TOKEN:
            return False, "Taqnyat not configured. Missing TAQNYAT_BEARER_TOKEN"
        if not settings.TAQNYAT_SENDER_NAME:
            return False, "Taqnyat not configured. Missing TAQNYAT_SENDER_NAME"
        return True, ""

    @staticmethod
    def _post_verify(payload: dict[str, Any]) -> tuple[bool, str, int | None]:
        configured, error = TaqnyatVerifyService._is_configured()
        if not configured:
            return False, error, None

        body = json.dumps([payload]).encode("utf-8")
        request = urllib.request.Request(
            VERIFY_URL,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.TAQNYAT_BEARER_TOKEN}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else str(exc)
            logger.error("Taqnyat Verify HTTP error: %s - %s", exc.code, raw)
            return False, f"Failed to contact Taqnyat Verify: HTTP {exc.code}", None
        except urllib.error.URLError as exc:
            logger.error("Taqnyat Verify connection error: %s", exc)
            return False, "Failed to contact Taqnyat Verify", None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Taqnyat Verify invalid JSON response: %s", raw)
            return False, "Invalid response from Taqnyat Verify", None

        if isinstance(parsed, list) and parsed:
            parsed = parsed[0]

        code = parsed.get("code") if isinstance(parsed, dict) else None
        message = parsed.get("message", "") if isinstance(parsed, dict) else raw
        return True, str(message), code

    @staticmethod
    def _build_payload(
        phone_number: str,
        request_id: str,
        lang: str,
        active_key: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "apiKey": settings.TAQNYAT_BEARER_TOKEN,
            "numbers": [format_phone_for_taqnyat(phone_number)],
            "method": "sms",
            "sender": settings.TAQNYAT_SENDER_NAME,
            "lang": lang,
            "requestId": request_id,
            "returnJson": 1,
        }
        if active_key is not None:
            payload["activeKey"] = active_key
        return payload

    @staticmethod
    def send_verification_code(
        phone_number: str,
        request_id: str,
        lang: str = "ar",
    ) -> tuple[bool, str]:
        payload = TaqnyatVerifyService._build_payload(phone_number, request_id, lang)
        ok, message, code = TaqnyatVerifyService._post_verify(payload)

        if not ok:
            return False, message

        if code == VERIFY_CODE_SENT:
            logger.info(
                "Taqnyat Verify OTP sent. requestId=%s, phone=%s",
                request_id,
                format_phone_for_taqnyat(phone_number),
            )
            return True, "Verification code sent successfully"

        if code == VERIFY_ALREADY_SENT:
            return True, "Verification code already sent. Please wait before resending."

        if code == VERIFY_SEND_ATTEMPTS_EXCEEDED:
            return False, "Too many OTP requests. Please try again later."

        logger.error("Taqnyat Verify send failed: code=%s message=%s", code, message)
        return False, TaqnyatVerifyService._map_error_code(code, message)

    @staticmethod
    def verify_code(
        phone_number: str,
        request_id: str,
        code: str,
        lang: str = "ar",
    ) -> tuple[bool, str]:
        payload = TaqnyatVerifyService._build_payload(
            phone_number, request_id, lang, active_key=code
        )
        ok, message, response_code = TaqnyatVerifyService._post_verify(payload)

        if not ok:
            return False, message

        if response_code in (VERIFY_SUCCESS, VERIFY_ALREADY_ACTIVATED, VERIFY_NUMBER_ALREADY_VERIFIED):
            logger.info(
                "Taqnyat Verify success. requestId=%s, phone=%s",
                request_id,
                format_phone_for_taqnyat(phone_number),
            )
            return True, "Phone verified successfully!"

        if response_code == VERIFY_INCORRECT:
            return False, "Invalid or expired verification code"

        if response_code == VERIFY_ATTEMPTS_EXHAUSTED:
            return False, "Too many incorrect attempts. Please request a new OTP."

        logger.warning(
            "Taqnyat Verify check failed: code=%s message=%s", response_code, message
        )
        return False, TaqnyatVerifyService._map_error_code(response_code, message)

    @staticmethod
    def _map_error_code(code: int | None, message: str) -> str:
        mapping = {
            0: "Connection failed to Taqnyat server",
            1: "Invalid Taqnyat API credentials",
            3: "Mobile number is not specified or incorrect",
            4: "Insufficient Taqnyat balance",
            6: "Taqnyat service error. Please contact support.",
        }
        if code in mapping:
            return mapping[code]
        return message or "Failed to process verification request"


class TaqnyatSMSService:
    """Taqnyat SMS API for sending OTP messages (e.g. rider verification)."""

    @staticmethod
    def send_otp_sms(phone_number: str, otp_code: str) -> tuple[bool, str]:
        configured, error = TaqnyatVerifyService._is_configured()
        if not configured:
            return False, error

        body_text = (
            f"Your Mgask verification code is: {otp_code}. "
            f"Valid for {getattr(settings, 'OTP_EXPIRY_MINUTES', 5)} minutes."
        )
        payload = json.dumps(
            {
                "recipients": [format_phone_for_taqnyat(phone_number)],
                "body": body_text,
                "sender": settings.TAQNYAT_SENDER_NAME,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            SMS_URL,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.TAQNYAT_BEARER_TOKEN}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode("utf-8")
                parsed = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else str(exc)
            logger.error("Taqnyat SMS HTTP error: %s - %s", exc.code, raw)
            return False, f"Failed to send SMS: HTTP {exc.code}"
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.error("Taqnyat SMS error: %s", exc)
            return False, f"Failed to send SMS: {exc}"

        status_code = parsed.get("statusCode") if isinstance(parsed, dict) else None
        if status_code == 201:
            message_id = parsed.get("messageId", "")
            logger.info("Taqnyat SMS sent. messageId=%s", message_id)
            return True, f"SMS sent successfully. messageId: {message_id}"

        error_message = parsed.get("message", "Unknown error") if isinstance(parsed, dict) else raw
        return False, f"Failed to send SMS: {error_message}"
