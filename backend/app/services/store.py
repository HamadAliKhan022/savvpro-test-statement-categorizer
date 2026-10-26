"""In-memory store for processed statements and manual review overrides.

Financial conventions (documented in DESIGN.md):
- Income metrics count positive Business Income and Interest Income only.
- Refunds/credits are reported separately and are never counted as income.
- Expenses count negative amounts excluding Transfers & Internal, so moving
  money between the owner's own accounts never inflates business expenses.
- Net cash flow is the plain sum of every transaction amount.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..engine.brain import (
    ALL_CATEGORIES,
    NEEDS_REVIEW_CATEGORY,
    STATUS_REVIEWED,
)

INCOME_REPORTED_CATEGORIES = {"Business Income", "Interest Income"}
REFUND_CATEGORY = "Refund / Credit"
TRANSFER_CATEGORY = "Transfers & Internal"

SOURCE_ENGINE = "engine"
SOURCE_IMPORTED = "imported"
SOURCE_MANUAL = "manual"


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _category_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return _NON_ALNUM.sub("", text)


_CATEGORY_LOOKUP = {_category_key(name): name for name in ALL_CATEGORIES}


def canonical_category(value: Optional[str]) -> Optional[str]:
    """Map a spreadsheet label onto the taxonomy, or None if unknown.

    Case, accents and punctuation are ignored so "software & subscriptions"
    from a hand-edited export still resolves, but arbitrary labels such as
    "Office Supplies" or "Adobe" are refused rather than guessed at.
    """
    if not value:
        return None
    return _CATEGORY_LOOKUP.get(_category_key(value))


def transaction_type(category: str, amount: float) -> str:
    if category == REFUND_CATEGORY:
        return "refund"
    if category == TRANSFER_CATEGORY:
        return "transfer"
    if category == NEEDS_REVIEW_CATEGORY:
        return "uncategorized"
    if category in INCOME_REPORTED_CATEGORIES:
        return "income"
    return "expense" if amount < 0 else "income"


@dataclass
class Transaction:
    id: str
    date: str
    description: str
    amount: float
    category: str
    status: str
    matched_rule: Optional[str]
    reason: str
    source: str = SOURCE_ENGINE  # engine | imported | manual
    original_category: Optional[str] = None  # engine category before manual edit
    source_row: Optional[int] = None  # line/position in the uploaded file

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "amount": self.amount,
            "category": self.category,
            "status": self.status,
            "source": self.source,
            "transaction_type": transaction_type(self.category, self.amount),
            "matched_rule": self.matched_rule,
            "reason": self.reason,
            "original_category": self.original_category,
            "source_row": self.source_row,
            "manually_overridden": self.original_category is not None,
        }


@dataclass
class Statement:
    id: str
    filename: str
    uploaded_at: str
    transactions: List[Transaction]
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> dict:
        total = len(self.transactions)
        needs_review = sum(1 for t in self.transactions if t.status == "Needs Review")
        income = sum(
            t.amount
            for t in self.transactions
            if t.amount > 0 and t.category in INCOME_REPORTED_CATEGORIES
        )
        refunds = sum(
            t.amount for t in self.transactions if t.category == REFUND_CATEGORY and t.amount > 0
        )
        expenses = sum(
            t.amount
            for t in self.transactions
            if t.amount < 0 and t.category != TRANSFER_CATEGORY
        )
        transfers = sum(
            t.amount for t in self.transactions if t.category == TRANSFER_CATEGORY
        )
        net_cash_flow = sum(t.amount for t in self.transactions)
        by_category: Dict[str, dict] = {}
        for t in self.transactions:
            bucket = by_category.setdefault(
                t.category, {"category": t.category, "count": 0, "total": 0.0}
            )
            bucket["count"] += 1
            bucket["total"] = round(bucket["total"] + t.amount, 2)
        return {
            "statement_id": self.id,
            "filename": self.filename,
            "uploaded_at": self.uploaded_at,
            "total_transactions": total,
            "needs_review_count": needs_review,
            "reviewed_count": total - needs_review,
            "total_income": round(income, 2),
            "total_refunds": round(refunds, 2),
            "total_expenses": round(expenses, 2),
            "total_transfers": round(transfers, 2),
            "net_cash_flow": round(net_cash_flow, 2),
            "by_category": sorted(
                by_category.values(), key=lambda row: abs(row["total"]), reverse=True
            ),
        }


class StatementStore:
    """Process-local store; statements live in server memory only and are
    never written to disk or forwarded to third-party services."""

    def __init__(self) -> None:
        self._statements: Dict[str, Statement] = {}

    def create(
        self, filename: str, transactions: List[Transaction], warnings: List[str]
    ) -> Statement:
        statement = Statement(
            id=uuid.uuid4().hex[:12],
            filename=filename,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            transactions=transactions,
            warnings=warnings,
        )
        self._statements[statement.id] = statement
        return statement

    def get(self, statement_id: str) -> Optional[Statement]:
        return self._statements.get(statement_id)

    def override_category(
        self, statement_id: str, transaction_id: str, category: str
    ) -> Optional[Transaction]:
        statement = self._statements.get(statement_id)
        if statement is None or category not in ALL_CATEGORIES:
            return None
        for transaction in statement.transactions:
            if transaction.id == transaction_id:
                if transaction.original_category is None:
                    transaction.original_category = transaction.category
                transaction.category = category
                transaction.status = STATUS_REVIEWED
                transaction.source = SOURCE_MANUAL
                transaction.reason = "Category set manually during review."
                return transaction
        return None


store = StatementStore()
