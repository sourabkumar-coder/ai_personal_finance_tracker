import logging
import os
from datetime import date, datetime
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.database.models import SmsAlertLog

logger = logging.getLogger(__name__)

TEXTBEE_SEND_URL = "/gateway/send-sms"
DEFAULT_BASE_URL = "https://api.textbee.dev/api/v1"
DEFAULT_DAILY_CAP = 10  # well under TextBee's 50 SMS/day free quota


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


class SmsService:
    """Outbound SMS alerts via TextBee (https://textbee.dev).

    Quota safeguards (TextBee free tier = 50 SMS/day):
    - one SMS per (student, category, month, level) via SmsAlertLog dedupe
    - global daily cap via BUDGET_SMS_DAILY_CAP (default 10)
    - TEXTBEE_DRY_RUN=true logs instead of sending (for safe testing)
    - failures never raise: expense logging must not break if SMS fails
    """

    @staticmethod
    def _config() -> Dict[str, Any]:
        return {
            "api_key": os.getenv("TEXTBEE_API_KEY", "").strip(),
            "device_id": os.getenv("TEXTBEE_DEVICE_ID", "").strip() or None,
            "recipient": os.getenv("BUDGET_SMS_RECIPIENT", "").strip(),
            "enabled": _env_flag("BUDGET_SMS_ENABLED", True),
            "dry_run": _env_flag("TEXTBEE_DRY_RUN", False),
            "base_url": os.getenv("TEXTBEE_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            "daily_cap": int(os.getenv("BUDGET_SMS_DAILY_CAP", str(DEFAULT_DAILY_CAP))),
        }

    @staticmethod
    def build_budget_message(
        level: str, category: str, total_spent: float, monthly_limit: float, percentage: float
    ) -> str:
        """Short ASCII-only message (keeps it to a single GSM SMS segment)."""
        if level == "exceeded":
            return (
                f"SmartFinance: {category} budget EXCEEDED. "
                f"Spent Rs.{total_spent:,.0f} of Rs.{monthly_limit:,.0f} ({percentage:.0f}%)."
            )
        return (
            f"SmartFinance: {category} budget at {percentage:.0f}%. "
            f"Spent Rs.{total_spent:,.0f} of Rs.{monthly_limit:,.0f}. Slow down!"
        )

    @staticmethod
    def _send_via_textbee(message: str, cfg: Dict[str, Any]) -> bool:
        payload: Dict[str, Any] = {
            "recipients": [cfg["recipient"]],
            "message": message,
        }
        if cfg["device_id"]:
            payload["deviceId"] = cfg["device_id"]
        resp = httpx.post(
            f"{cfg['base_url']}{TEXTBEE_SEND_URL}",
            json=payload,
            headers={"x-api-key": cfg["api_key"], "Content-Type": "application/json"},
            timeout=8.0,
        )
        if 200 <= resp.status_code < 300:
            return True
        logger.warning("TextBee send failed: HTTP %s: %s", resp.status_code, resp.text[:200])
        return False

    @staticmethod
    def maybe_send_budget_alert(
        db: Session,
        student_id: int,
        alert: Optional[Dict[str, Any]],
        year: int = None,
        month: int = None,
    ) -> Dict[str, Any]:
        """Send a budget SMS for a warning/exceeded alert, at most once per category per month.

        Returns {"sent": bool, "reason": str}. Never raises.
        """
        try:
            if not alert or (not alert.get("is_exceeded") and not alert.get("is_warning")):
                return {"sent": False, "reason": "no_alert"}

            cfg = SmsService._config()
            if not cfg["enabled"]:
                return {"sent": False, "reason": "disabled"}
            if not cfg["api_key"] or not cfg["recipient"]:
                return {"sent": False, "reason": "not_configured"}

            level = "exceeded" if alert.get("is_exceeded") else "warning"
            today = date.today()
            target_year = year or today.year
            target_month = month or today.month
            category = str(alert.get("category", "Budget"))

            duplicate = (
                db.query(SmsAlertLog)
                .filter(
                    SmsAlertLog.student_id == student_id,
                    SmsAlertLog.category == category,
                    SmsAlertLog.level == level,
                    SmsAlertLog.year == target_year,
                    SmsAlertLog.month == target_month,
                )
                .first()
            )
            if duplicate:
                return {"sent": False, "reason": "duplicate"}

            sent_today = (
                db.query(SmsAlertLog)
                .filter(SmsAlertLog.sent_at >= datetime(today.year, today.month, today.day))
                .count()
            )
            if sent_today >= cfg["daily_cap"]:
                logger.warning("Budget SMS daily cap (%s) reached, skipping.", cfg["daily_cap"])
                return {"sent": False, "reason": "daily_cap"}

            message = SmsService.build_budget_message(
                level,
                category,
                float(alert.get("total_spent", 0.0)),
                float(alert.get("monthly_limit", 0.0)),
                float(alert.get("percentage_used", 0.0)),
            )

            if cfg["dry_run"]:
                logger.info("[DRY RUN] Would SMS %s: %s", cfg["recipient"], message)
                return {"sent": False, "reason": "dry_run"}

            if not SmsService._send_via_textbee(message, cfg):
                return {"sent": False, "reason": "send_failed"}

            db.add(SmsAlertLog(
                student_id=student_id,
                category=category,
                level=level,
                year=target_year,
                month=target_month,
            ))
            db.commit()
            logger.info("Budget SMS sent (%s/%s) to %s.", category, level, cfg["recipient"])
            return {"sent": True, "reason": "sent"}
        except Exception as exc:  # never break expense logging because of SMS
            logger.warning("Budget SMS skipped due to error: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass
            return {"sent": False, "reason": "error"}
