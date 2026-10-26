"""Statement upload and review endpoints."""

from __future__ import annotations

import os
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..engine.brain import (
    ALL_CATEGORIES,
    NEEDS_REVIEW_CATEGORY,
    STATUS_NEEDS_REVIEW,
    STATUS_REVIEWED,
    categorize,
    find_duplicate_pairs,
)
from ..models import CategoriesResponse, HealthResponse, OverrideRequest
from ..services.parser import ParseError, parse_statement
from ..services.store import SOURCE_IMPORTED, Statement, Transaction, canonical_category, store

router = APIRouter(prefix="/api", tags=["statements"])

DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def max_upload_bytes() -> int:
    """MAX_UPLOAD_BYTES in bytes, so a deploy can raise the limit without a code change."""
    configured = os.getenv("MAX_UPLOAD_BYTES")
    if not configured or not configured.strip().isdigit():
        return DEFAULT_MAX_BYTES
    return int(configured.strip())


MAX_BYTES = max_upload_bytes()


def _statement_response(statement: Statement) -> dict:
    return {
        "summary": statement.summary(),
        "transactions": [t.to_dict() for t in statement.transactions],
        "warnings": statement.warnings,
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", engine="deterministic-rule-engine-v1", llm_used=False)


@router.get("/categories", response_model=CategoriesResponse)
def categories() -> CategoriesResponse:
    return CategoriesResponse(categories=ALL_CATEGORIES)


@router.post("/statements")
async def upload_statement(file: UploadFile = File(...)) -> dict:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(
            413, f"The file is larger than the {MAX_BYTES // (1024 * 1024)} MB limit."
        )
    if not content.strip():
        raise HTTPException(400, "The uploaded file is empty.")
    try:
        frame, warnings = parse_statement(content, file.filename or "statement.csv")
    except ParseError as exc:
        raise HTTPException(422, str(exc))

    rows = list(frame.itertuples())
    duplicates = find_duplicate_pairs(
        [(row.date, row.description, row.amount) for row in rows]
    )

    transactions: List[Transaction] = []
    for index, row in enumerate(rows):
        imported = canonical_category(getattr(row, "imported_category", "") or "")
        if imported and imported != NEEDS_REVIEW_CATEGORY:
            # A category carried in from a previously reviewed export is
            # preserved and labelled, but the row was still fully validated
            # by the parser and is still checked for duplicates below.
            decision_category, decision_status = imported, STATUS_REVIEWED
            decision_rule, decision_reason = None, (
                "Category imported from the uploaded file (previously reviewed)."
            )
            source = SOURCE_IMPORTED
        else:
            decision = categorize(row.description, row.amount)
            decision_category, decision_status = decision.category, decision.status
            decision_rule, decision_reason = decision.rule, decision.reason
            source = "engine"
        if index in duplicates:
            decision_status = STATUS_NEEDS_REVIEW
            decision_reason = (
                f"Possible duplicate of the transaction on source row "
                f"{rows[duplicates[index]].original_index}; flagged for review, "
                "not removed."
            )
        transactions.append(
            Transaction(
                id=uuid.uuid4().hex[:10],
                date=row.date,
                description=row.description,
                amount=round(float(row.amount), 2),
                category=decision_category,
                status=decision_status,
                matched_rule=decision_rule,
                reason=decision_reason,
                source=source,
                source_row=getattr(row, "original_index", None),
            )
        )
    statement = store.create(file.filename or "statement", transactions, warnings)
    return _statement_response(statement)


@router.get("/statements/{statement_id}")
def get_statement(statement_id: str) -> dict:
    statement = store.get(statement_id)
    if statement is None:
        raise HTTPException(404, "Statement not found. Upload the file again.")
    return _statement_response(statement)


@router.patch("/statements/{statement_id}/transactions/{transaction_id}")
def override_transaction(statement_id: str, transaction_id: str, payload: OverrideRequest) -> dict:
    transaction = store.override_category(statement_id, transaction_id, payload.category)
    if transaction is None:
        raise HTTPException(404, "Transaction or statement not found (or category unknown).")
    return {"transaction": transaction.to_dict(), "summary": store.get(statement_id).summary()}
