"""Review-flow tests: financial semantics, duplicates, imported categories,
and the export -> edit -> re-upload round trip. Synthetic data only."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPORT_HEADER = (
    "Date,Description,Amount,Category,Transaction Type,Status,Source,"
    "Engine Rule,Explanation,Manual Override"
)


def _upload(text: str, filename: str = "s.csv"):
    return client.post("/api/statements", files={"file": (filename, text.encode(), "text/csv")})


class TestFinancialSemantics:
    def test_refunds_are_not_income(self):
        response = _upload(
            "Date,Description,Amount\n"
            "2026-01-05,ACME CLIENT PAYMENT,1000.00\n"
            "2026-01-06,BEST BUY REFUND,129.99\n"
        )
        summary = response.json()["summary"]
        assert summary["total_income"] == pytest.approx(1000.00)
        assert summary["total_refunds"] == pytest.approx(129.99)
        assert summary["net_cash_flow"] == pytest.approx(1129.99)

    def test_transfers_are_not_expenses_or_income(self):
        response = _upload(
            "Date,Description,Amount\n"
            "2026-01-05,INTERNAL TRANSFER FROM SAVINGS,-500.00\n"
            "2026-01-06,STARBUCKS,-5.00\n"
        )
        summary = response.json()["summary"]
        assert summary["total_expenses"] == pytest.approx(-5.00)
        assert summary["total_transfers"] == pytest.approx(-500.00)
        assert summary["net_cash_flow"] == pytest.approx(-505.00)

    def test_totals_update_after_manual_correction(self):
        response = _upload(
            "Date,Description,Amount\n2026-01-05,MYSTERY MERCHANT,-80.00\n"
        )
        body = response.json()
        statement_id = body["summary"]["statement_id"]
        tx_id = body["transactions"][0]["id"]
        patched = client.patch(
            f"/api/statements/{statement_id}/transactions/{tx_id}",
            json={"category": "Transfers & Internal"},
        )
        summary = patched.json()["summary"]
        assert summary["total_expenses"] == pytest.approx(0.0)
        assert summary["total_transfers"] == pytest.approx(-80.0)


class TestDuplicates:
    def test_duplicate_rows_flagged_not_dropped(self):
        response = _upload(
            "Date,Description,Amount\n"
            "2026-01-05,UBER TRIP,-23.40\n"
            "2026-01-05,UBER TRIP,-23.40\n"
        )
        body = response.json()
        first, second = body["transactions"]
        assert first["status"] == "Reviewed"
        assert second["status"] == "Needs Review"
        assert "duplicate" in second["reason"].lower()
        assert body["summary"]["total_transactions"] == 2

    def test_different_amount_is_not_a_duplicate(self):
        response = _upload(
            "Date,Description,Amount\n"
            "2026-01-05,UBER TRIP,-23.40\n2026-01-05,UBER TRIP,-24.40\n"
        )
        assert all(t["status"] == "Reviewed" for t in response.json()["transactions"])


class TestImportedCategories:
    def test_valid_imported_category_preserved_and_labelled(self):
        response = _upload(
            EXPORT_HEADER + "\n"
            "2026-01-05,WEIRD MERCHANT CO,-80.00,Travel,expense,Reviewed,manual,,"
            "Category set manually during review.,yes\n"
        )
        transaction = response.json()["transactions"][0]
        assert transaction["category"] == "Travel"
        assert transaction["source"] == "imported"
        assert transaction["status"] == "Reviewed"

    def test_invalid_imported_category_falls_back_to_engine(self):
        response = _upload(
            EXPORT_HEADER + "\n"
            "2026-01-05,STARBUCKS STORE,-6.00,Crypto Gains,expense,Reviewed,manual,,"
            "whatever,no\n"
        )
        transaction = response.json()["transactions"][0]
        assert transaction["category"] == "Meals & Entertainment"
        assert transaction["source"] == "engine"

    def test_imported_category_still_checked_for_duplicates(self):
        row = (
            "2026-01-05,ACME PAYMENT,100.00,Business Income,income,Reviewed,imported,"
            "client_income,x,no"
        )
        response = _upload(EXPORT_HEADER + "\n" + row + "\n" + row + "\n")
        second = response.json()["transactions"][1]
        assert second["status"] == "Needs Review"
        assert "duplicate" in second["reason"].lower()


class TestExportRoundTrip:
    def test_export_then_reupload_is_lossless(self):
        original = _upload(
            "Date,Description,Amount\n"
            '2026-01-05,"AMAZON MARKETPLACE, ORDER 123",-42.00\n'
            "2026-01-06,ACME CLIENT PAYMENT,1000.00\n"
            "2026-01-07,MYSTERY VENDOR,-9.00\n"
        ).json()
        # Reassign every flagged row exactly as the UI does.
        statement_id = original["summary"]["statement_id"]
        transactions = list(original["transactions"])
        for index, tx in enumerate(transactions):
            if tx["status"] != "Needs Review":
                continue
            patched = client.patch(
                f"/api/statements/{statement_id}/transactions/{tx['id']}",
                json={"category": "Office & Equipment"},
            ).json()
            transactions[index] = patched["transaction"]

        # Build the CSV the frontend exporter produces and re-upload it.
        lines = [EXPORT_HEADER]
        for t in transactions:
            def esc(v):
                v = str(v if v is not None else "")
                return '"' + v.replace('"', '""') + '"' if any(c in v for c in ',"\n') else v
            lines.append(",".join([
                t["date"], esc(t["description"]), f"{t['amount']:.2f}", esc(t["category"]),
                t["transaction_type"], t["status"], t["source"], esc(t["matched_rule"] or ""),
                esc(t["reason"]), "yes" if t["manually_overridden"] else "no",
            ]))
        reupload = _upload("\n".join(lines) + "\n", "statementiq-sample-export.csv").json()

        assert reupload["warnings"] == []
        before = {(t["date"], t["description"], t["amount"], t["category"]) for t in transactions}
        after = {
            (t["date"], t["description"], t["amount"], t["category"])
            for t in reupload["transactions"]
        }
        assert before == after
        assert reupload["summary"]["needs_review_count"] == 0
        assert reupload["summary"]["total_expenses"] == pytest.approx(-51.00)


class TestParserWarningsSurfaceInApi:
    def test_bad_row_reported_with_line_number(self):
        response = _upload(
            "Date,Description,Amount\n"
            "2026-01-05,GOOD,-1.00\n"
            '2026-01-06,"BAD "ROW", -2.00, EXTRA\n'
        )
        assert response.status_code == 200
        warnings = response.json()["warnings"]
        assert len(warnings) == 1
        assert "Row 3" in warnings[0]

    def test_friendly_message_no_pandas_traceback(self):
        response = _upload("Date,Description,Amount\n2026-01-05,OK,-1.00\n", "x.json")
        # .json extension routes to JSON parsing; message must be user-readable.
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "Traceback" not in detail and "pandas" not in detail.lower()
