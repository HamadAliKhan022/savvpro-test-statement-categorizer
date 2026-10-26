"""Integration tests for the FastAPI endpoints (upload, summary, override)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CSV_CONTENT = (
    "Date,Description,Amount\n"
    "2026-01-05,ACME CLIENT PAYMENT INV 101,2500.00\n"
    "2026-01-07,Amazon Web Services *Compute,-84.21\n"
    "2026-01-08,Starbucks Store 1221,-6.45\n"
    "2026-01-11,KRUNK'S DISCOUNT MARINA,-77.00\n"
    "2026-01-15,AWS REFUND,84.21\n"
)

JSON_CONTENT = json.dumps(
    {
        "transactions": [
            {"date": "2026-02-01", "description": "UBER TRIP", "amount": -23.4},
            {"date": "2026-02-02", "description": "MYSTERY VENDOR", "amount": -10.0},
        ]
    }
)


def _upload(content: str, filename: str, ctype: str):
    return client.post(
        "/api/statements", files={"file": (filename, content.encode(), ctype)}
    )


class TestHealthAndCategories:
    def test_health(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["llm_used"] is False

    def test_categories(self):
        response = client.get("/api/categories")
        assert response.status_code == 200
        assert "Needs Review" not in response.json()["categories"]
        assert "Uncategorized" in response.json()["categories"]


class TestUpload:
    def test_csv_upload_and_summary(self):
        response = _upload(CSV_CONTENT, "january.csv", "text/csv")
        assert response.status_code == 200
        body = response.json()
        summary = body["summary"]
        assert summary["total_transactions"] == 5
        assert summary["needs_review_count"] == 1
        assert summary["reviewed_count"] == 4
        # Refunds are reported separately from income (documented convention).
        assert summary["total_income"] == pytest.approx(2500.00)
        assert summary["total_refunds"] == pytest.approx(84.21)
        assert summary["total_expenses"] == pytest.approx(-167.66)
        assert summary["net_cash_flow"] == pytest.approx(2584.21 - 167.66)
        categories = {t["description"]: t["category"] for t in body["transactions"]}
        assert categories["Amazon Web Services *Compute"] == "Software & Subscriptions"
        assert categories["AWS REFUND"] == "Refund / Credit"
        assert categories["KRUNK'S DISCOUNT MARINA"] == "Uncategorized"

    def test_json_upload(self):
        response = _upload(JSON_CONTENT, "february.json", "application/json")
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["total_transactions"] == 2
        assert body["summary"]["needs_review_count"] == 1

    def test_amount_with_currency_symbols(self):
        csv = 'Date,Description,Amount\n2026-03-01,Starbucks,"-$12,345.67"\n'
        response = _upload(csv, "mar.csv", "text/csv")
        assert response.status_code == 200
        assert response.json()["transactions"][0]["amount"] == -12345.67

    def test_rejects_garbage_file(self):
        response = _upload("this is not, a statement\njust prose", "bad.csv", "text/csv")
        assert response.status_code == 422

    def test_rejects_empty_file(self):
        response = _upload("", "empty.csv", "text/csv")
        assert response.status_code == 400

    def test_statement_retrievable_by_id(self):
        response = _upload(CSV_CONTENT, "again.csv", "text/csv")
        statement_id = response.json()["summary"]["statement_id"]
        fetched = client.get(f"/api/statements/{statement_id}")
        assert fetched.status_code == 200
        assert fetched.json()["summary"]["total_transactions"] == 5
        assert client.get("/api/statements/doesnotexist").status_code == 404


class TestManualOverride:
    def _flagged(self):
        response = _upload(CSV_CONTENT, "override.csv", "text/csv")
        body = response.json()
        flagged = [t for t in body["transactions"] if t["status"] == "Needs Review"][0]
        return body["summary"]["statement_id"], flagged

    def test_override_marks_reviewed_and_updates_summary(self):
        statement_id, flagged = self._flagged()
        response = client.patch(
            f"/api/statements/{statement_id}/transactions/{flagged['id']}",
            json={"category": "Travel"},
        )
        assert response.status_code == 200
        transaction = response.json()["transaction"]
        assert transaction["category"] == "Travel"
        assert transaction["status"] == "Reviewed"
        assert transaction["manually_overridden"] is True
        assert transaction["original_category"] == "Uncategorized"
        assert response.json()["summary"]["needs_review_count"] == 0

    def test_override_rejects_unknown_category(self):
        statement_id, flagged = self._flagged()
        response = client.patch(
            f"/api/statements/{statement_id}/transactions/{flagged['id']}",
            json={"category": "Crypto Gains"},
        )
        assert response.status_code == 404

    def test_override_unknown_transaction(self):
        statement_id, _ = self._flagged()
        response = client.patch(
            f"/api/statements/{statement_id}/transactions/nope",
            json={"category": "Travel"},
        )
        assert response.status_code == 404


class TestMessySampleEndToEnd:
    """The shipped 'real world' sample, through the whole HTTP path."""

    def _upload_sample(self):
        import pathlib

        path = (
            pathlib.Path(__file__).parent.parent
            / "sample_data"
            / "sample_messy_designer.csv"
        )
        return client.post(
            "/api/statements",
            files={"file": (path.name, path.read_bytes(), "text/csv")},
        )

    def test_uploads_with_layout_warnings_not_failures(self):
        response = self._upload_sample()
        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["total_transactions"] == 15
        joined = " ".join(body["warnings"])
        assert "Skipped 4 line(s) above the table header" in joined
        assert "repeated header" in joined
        assert "statement-total or balance row(s)" in joined
        assert "DD/MM/YYYY" in joined

    def test_footer_and_preamble_rows_never_reach_the_ledger(self):
        transactions = self._upload_sample().json()["transactions"]
        assert not any(t["description"].startswith("TOTAL ") and t["amount"] > 2000 for t in transactions)
        assert {t["category"] for t in transactions if "NORTH SHORE" in t["description"]} == set()

    def test_source_rows_point_back_at_the_uploaded_file(self):
        transactions = self._upload_sample().json()["transactions"]
        rows = {t["source_row"] for t in transactions}
        assert None not in rows
        assert len(rows) == len(transactions)  # one row each, nothing reused

    def test_disputes_and_opaque_terms_stay_for_a_human(self):
        transactions = self._upload_sample().json()["transactions"]
        flagged = {t["description"] for t in transactions if t["status"] == "Needs Review"}
        assert "POS PURCHASE #88421" in flagged
        assert "DISPUTE - ELECTRONIC ARTS SUBSCR" in flagged
        # …while a fee for that dispute is still an understood bank charge.
        reviewed = {t["description"] for t in transactions if t["status"] == "Reviewed"}
        assert "CHARGEBACK FEE" in reviewed
