"""
Modular financial transaction parser for UPI and Indian banking notifications.
Implements a multi-stage filtering pipeline to accurately extract transaction
entities and reject non-transactional alerts (OTPs, balance notifications, marketing).
"""
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple


# Known financial application packages
SUPPORTED_PACKAGES = {
    "com.google.android.apps.nbu.paisa.user": "Google Pay",
    "com.phonepe.app": "PhonePe",
    "net.one97.paytm": "Paytm",
    "in.org.npci.upiapp": "BHIM",
    "com.sbi.lotusintouch": "SBI YONO",
    "com.hdfcbank.android": "HDFC Bank",
    "com.icicibank.mobile": "iMobile Pay (ICICI)",
    "com.axis.mobile": "Axis Mobile",
    "com.msf.kbank.mobile": "Kotak 811",
    "com.csam.pnb": "PNB ONE",
    "com.bankofbaroda.mconnect": "bob World",
    "in.cred.app": "CRED",
    "com.amazon.mShop.android.shopping": "Amazon Pay",
}

# Known financial application titles or keywords
SUPPORTED_APP_NAMES = [
    "google pay", "gpay", "phonepe", "paytm", "bhim", "sbi", "hdfc", "icici",
    "axis", "kotak", "pnb", "bob", "cred", "bank", "upi", "amazon pay"
]

# Non-transactional patterns that must NEVER be recorded as expenses
NON_TRANSACTION_INDICATORS = [
    r"\bavailable balance\b",
    r"\bavl bal\b",
    r"\baccount balance\b",
    r"\bacct bal\b",
    r"\bbalance is\b",
    r"\botp\b",
    r"\bone time password\b",
    r"\bverification code\b",
    r"\bposted a story\b",
    r"\bshared a post\b",
    r"\bdiscount\b",
    r"\buse code\b",
    r"\bwin up to\b",
    r"\bflat \d+% off\b",
    r"\bsecurity alert\b",
]


class TransactionParser:
    """
    Modular parser for extracting transaction details from notification text.
    """

    @classmethod
    def is_supported_source(cls, package_name: Optional[str], app_title: Optional[str] = None) -> bool:
        """Stage 1: Verify source package or app title matches a supported financial application."""
        if package_name and package_name.strip().lower() in SUPPORTED_PACKAGES:
            return True
        combined = f"{package_name or ''} {app_title or ''}".lower()
        return any(app_name in combined for app_name in SUPPORTED_APP_NAMES)

    @classmethod
    def is_financial_signal(cls, text: str) -> bool:
        """Stage 2: Check for transaction-related keywords/symbols."""
        if not text:
            return False
        signals = [
            r"₹", r"inr", r"rs\.?", r"paid", r"debited", r"credited",
            r"received", r"sent", r"payment", r"transaction", r"spent", r"transferred"
        ]
        return any(re.search(sig, text, re.IGNORECASE) for sig in signals)

    @classmethod
    def is_blacklisted_alert(cls, text: str) -> Tuple[bool, Optional[str]]:
        """Stage 3: Reject non-transactional alerts (e.g. balance check, OTP, promo)."""
        lower = text.lower()
        for pattern in NON_TRANSACTION_INDICATORS:
            if re.search(pattern, lower):
                return True, f"Matched non-transaction pattern: '{pattern}'"
        return False, None

    @classmethod
    def extract_amount(cls, text: str) -> Optional[float]:
        """
        Extract numerical amount accurately.
        Handles currency symbols, commas, decimals (e.g. ₹1,200.50, INR 350, Rs 45).
        """
        patterns = [
            # ₹ 1,200.50 or Rs. 350 or INR 500
            r"(?:₹|rs\.?|inr)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]{1,2})?)",
            # payment of 350 or debited by 1,200
            r"(?:payment of|debited by|spent|amount of|sum of)\s*(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]{1,2})?)",
            # 500 paid or 1200 sent
            r"([0-9]+(?:,[0-9]+)*(?:\.[0-9]{1,2})?)\s*(?:paid|sent|debited|credited|received)",
        ]

        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                raw_amt = match.group(1).replace(",", "")
                try:
                    val = float(raw_amt)
                    if val > 0:
                        return round(val, 2)
                except ValueError:
                    continue
        return None

    @classmethod
    def extract_status(cls, text: str) -> str:
        """
        Extract transaction status: SUCCESS, FAILED, PENDING, CANCELLED, UNKNOWN.
        """
        lower = text.lower()
        # Check failed first
        if any(w in lower for w in ["failed", "declined", "unsuccessful", "rejected", "timed out", "couldn't be processed"]):
            return "FAILED"
        if any(w in lower for w in ["cancelled", "canceled", "reversed", "refunded"]):
            return "CANCELLED"
        if any(w in lower for w in ["pending", "processing", "in progress", "initiated", "awaiting"]):
            return "PENDING"
        if any(w in lower for w in ["successful", "success", "paid", "debited", "credited", "sent", "received", "completed", "done"]):
            return "SUCCESS"
        return "UNKNOWN"

    @classmethod
    def extract_transaction_type(cls, text: str) -> str:
        """
        Distinguish outgoing (EXPENSE) from incoming (INCOME).
        """
        lower = text.lower()
        credit_words = ["received from", "credited to", "credited with", "deposited", "refund received", "cashback received", "received ₹", "received inr"]
        debit_words = ["paid to", "sent to", "debited from", "transferred to", "spent at", "purchase at", "paid ₹", "paid inr"]

        for w in credit_words:
            if w in lower:
                return "INCOME"
        for w in debit_words:
            if w in lower:
                return "EXPENSE"

        if "credited" in lower or "received" in lower:
            return "INCOME"
        if "debited" in lower or "paid" in lower or "sent" in lower or "spent" in lower:
            return "EXPENSE"

        return "EXPENSE"

    @classmethod
    def extract_merchant(cls, text: str, title: Optional[str] = None) -> Optional[str]:
        """
        Extract merchant, business name, or counterparty.
        e.g.:
        "Payment of ₹350 to Zomato successful" -> "Zomato"
        "You paid ₹1200 to Amazon" -> "Amazon"
        "₹500 received from Rahul" -> "Rahul"
        """
        patterns = [
            # to/towards/at/paid to/from <Merchant/Person> (followed by delimiter, status keyword, or end of string)
            r"(?:to|towards|at|paid to|sent to|spent at|received from|from)\s+([A-Za-z0-9\s&'\.-]+?)(?=(?:\s+(?:successful|success|completed|using|via|on|ref|upi|for|with|into)|\.|$))",
            # paid <Merchant>
            r"(?:paid)\s+([A-Za-z0-9\s&'\.-]+?)(?=(?:\s+(?:successful|success|using|via|on|ref)|\.|$))",
            # VPA: merchant@bank
            r"([a-zA-Z0-9\.-]+@[a-zA-Z]+)",
        ]

        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                cleaned = cls._clean_merchant_candidate(candidate)
                if cleaned:
                    return cleaned

        # Check if title has the merchant name
        if title:
            cleaned_title = cls._clean_merchant_candidate(title)
            if cleaned_title and cleaned_title.lower() not in ["google pay", "phonepe", "paytm", "bhim", "upi", "bank", "sms", "alert"]:
                return cleaned_title

        return "Unknown Merchant"

    @classmethod
    def _clean_merchant_candidate(cls, candidate: str) -> Optional[str]:
        """Clean noise and prefixes from candidate merchant string."""
        if not candidate:
            return None
        # Remove trailing symbols/words
        clean = re.sub(r"[,\.:;]+$", "", candidate).strip()
        stop_words = ["a", "an", "the", "your", "my", "account", "vpa", "upi", "card", "bank"]
        if clean.lower() in stop_words:
            return None
        if len(clean) < 2 or len(clean) > 80:
            return None
        # Capitalize nicely if all lower
        if clean.islower():
            clean = clean.title()
        return clean

    @classmethod
    def extract_upi_reference(cls, text: str) -> Optional[str]:
        """Extract UTR, UPI Reference Number, or Txn ID."""
        patterns = [
            r"(?:upi\s*ref(?:erence)?\s*(?:no\.?|num)?|utr|txn\s*(?:id)?)\s*[:\-]?\s*([A-Za-z0-9]{8,22})",
            r"\b(ref\s*(?:no\.?)?\s*([0-9]{12}))\b",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @classmethod
    def parse_notification(
        cls,
        text: str,
        title: Optional[str] = None,
        package_name: Optional[str] = None,
        source_app: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute full parsing pipeline on an incoming notification.
        Returns a dictionary containing structured fields and validation status.
        """
        result = {
            "is_valid_transaction": False,
            "rejection_reason": None,
            "amount": None,
            "merchant": None,
            "transaction_type": "EXPENSE",
            "status": "UNKNOWN",
            "payment_method": "UPI",
            "source_app": source_app or (SUPPORTED_PACKAGES.get(package_name or "") or title or "UPI App"),
            "reference": None,
            "raw_text": text,
        }

        # Stage 1: Check source
        if package_name and not cls.is_supported_source(package_name, title):
            result["rejection_reason"] = f"Unsupported source application: {package_name}"
            return result

        # Stage 2: Check financial signal
        full_text = f"{title or ''} {text}".strip()
        if not cls.is_financial_signal(full_text):
            result["rejection_reason"] = "No financial or currency signals detected in notification text"
            return result

        # Stage 3: Reject non-transactional alerts (balance, OTP, stories)
        is_blacklisted, reason = cls.is_blacklisted_alert(full_text)
        if is_blacklisted:
            result["rejection_reason"] = reason
            return result

        # Stage 4: Extract amount
        amount = cls.extract_amount(full_text)
        if not amount or amount <= 0:
            result["rejection_reason"] = "Could not extract a valid transaction amount"
            return result
        result["amount"] = amount

        # Stage 5: Extract status
        status = cls.extract_status(full_text)
        result["status"] = status
        if status in ["FAILED", "CANCELLED"]:
            result["rejection_reason"] = f"Transaction was not successful (status={status})"
            return result

        # Stage 6: Extract type (EXPENSE vs INCOME)
        result["transaction_type"] = cls.extract_transaction_type(full_text)

        # Stage 7: Extract merchant
        merchant = cls.extract_merchant(text, title)
        result["merchant"] = merchant or "Unknown Merchant"

        # Stage 8: Extract UPI Reference
        result["reference"] = cls.extract_upi_reference(full_text)

        result["is_valid_transaction"] = True
        return result
