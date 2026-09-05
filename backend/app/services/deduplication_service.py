"""
Deduplication Service for Financial Transactions.
Prevents multiple notifications for the same payment (e.g. UPI app notification
+ bank SMS alert) from creating duplicate expense records.
"""
import hashlib
from datetime import datetime, timedelta, date as dt_date, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.database.models import Expense


class DeduplicationService:
    """
    Computes deterministic transaction fingerprints and identifies duplicate records
    within a configurable time window.
    """

    @classmethod
    def generate_fingerprint(
        cls,
        student_id: int,
        amount: float,
        merchant: str,
        txn_date: dt_date,
        reference: Optional[str] = None,
    ) -> str:
        """
        Generate a unique 64-character SHA-256 fingerprint for a transaction.
        If a unique reference (UTR/TxnID) is available, use it.
        Otherwise, hash student_id, rounded amount, normalized merchant, and date.
        """
        if reference and len(reference.strip()) >= 6:
            raw = f"{student_id}:ref:{reference.strip().lower()}"
        else:
            norm_merchant = (merchant or "unknown").strip().lower()
            raw = f"{student_id}:{round(amount, 2)}:{norm_merchant}:{txn_date.isoformat()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def is_duplicate(
        cls,
        db: Session,
        student_id: int,
        amount: float,
        merchant: str,
        fingerprint: str,
        txn_timestamp: Optional[datetime] = None,
        window_minutes: int = 15,
    ) -> Tuple[bool, Optional[Expense]]:
        """
        Check if an identical transaction already exists in the database.
        Checks:
        1. Exact fingerprint match.
        2. Same student, same amount (+/- 0.01), similar merchant, within a 15-minute window.
        """
        # 1. Exact fingerprint match
        if fingerprint:
            existing = (
                db.query(Expense)
                .filter(
                    Expense.student_id == student_id,
                    Expense.fingerprint == fingerprint,
                )
                .first()
            )
            if existing:
                return True, existing

        # 2. Sliding time window check
        norm_merchant = (merchant or "").strip().lower()
        now = txn_timestamp or datetime.now(timezone.utc)
        start_window = now - timedelta(minutes=window_minutes)
        end_window = now + timedelta(minutes=window_minutes)

        potential_dupes = (
            db.query(Expense)
            .filter(
                Expense.student_id == student_id,
                Expense.amount == round(amount, 2),
                Expense.created_at >= start_window,
                Expense.created_at <= end_window,
            )
            .all()
        )

        for exp in potential_dupes:
            exp_merchant = (exp.merchant or exp.title or "").strip().lower()
            if norm_merchant and (norm_merchant in exp_merchant or exp_merchant in norm_merchant):
                return True, exp

        return False, None
