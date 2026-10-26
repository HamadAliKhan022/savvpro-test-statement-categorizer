"""Unit tests for the deterministic Decision Engine (brain.py).

These tests pin down the contract: exact matches, polarity handling
(positive = income/refund), and the fail-safe "Needs Review" policy.
"""

import ast
from pathlib import Path

import pytest

from app.engine.brain import (
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    NEEDS_REVIEW_CATEGORY,
    STATUS_NEEDS_REVIEW,
    STATUS_REVIEWED,
    categorize,
    normalize_description,
)


class TestNormalize:
    def test_lowercases_and_strips_punctuation(self):
        assert normalize_description("  STARBUCKS #50234!! ") == "starbucks 50234"

    def test_collapses_whitespace(self):
        assert normalize_description("AWS--Web___Services") == "aws web services"

    def test_empty(self):
        assert normalize_description("") == ""


class TestExpenseMatching:
    @pytest.mark.parametrize(
        "description,amount,category",
        [
            ("UBER TRIP HELP. MY DRIVE", -23.40, "Travel"),
            ("Starbucks Store 1221", -6.00, "Meals & Entertainment"),
            ("Amazon Web Services *Compute", -84.21, "Software & Subscriptions"),
            ("MSFT*OFFICE 365", -99.99, "Software & Subscriptions"),
            ("FedEx Ship Store", -14.00, "Professional Services"),
            ("Verizon Wireless Bill", -65.00, "Utilities & Telecom"),
            ("WeWork Membership", -350.00, "Rent & Occupancy"),
            ("GEICO AUTO PREMIUM", -120.00, "Insurance"),
            ("Google Ads Campaign", -200.00, "Marketing & Advertising"),
            ("Staples 0442", -31.10, "Office & Equipment"),
        ],
    )
    def test_expense_rules(self, description, amount, category):
        decision = categorize(description, amount)
        assert decision.status == STATUS_REVIEWED
        assert decision.category == category
        assert decision.rule is not None

    def test_case_insensitive(self):
        assert categorize("starbucks", -6.0).category == "Meals & Entertainment"
        assert categorize("STARBUCKS", -6.0).category == "Meals & Entertainment"

    def test_specific_rule_beats_generic(self):
        # 'monthly service fee' (fees rule) must win over 'monthly service' (software).
        decision = categorize("MONTHLY SERVICE FEE", -9.99)
        assert decision.category == "Banking & Finance Fees"


class TestIncomeAndRefunds:
    def test_positive_client_payment_is_business_income(self):
        decision = categorize("ACME CLIENT PAYMENT INV 2041", 1500.0)
        assert decision.category == "Business Income"
        assert decision.status == STATUS_REVIEWED

    def test_positive_expense_merchant_is_recorded_as_refund(self):
        decision = categorize("Amazon Web Services Refund", 84.21)
        assert decision.category == "Refund / Credit"

    def test_positive_expense_match_never_stays_expense(self):
        # Even when the merchant matches an expense rule, a positive amount
        # must never be categorized as an expense category.
        decision = categorize("UBER CREDIT", 23.0)
        assert decision.category not in EXPENSE_CATEGORIES

    def test_interest_payment(self):
        assert categorize("INTEREST PAYMENT POSTED", 4.20).category == "Interest Income"

    def test_payout(self):
        assert categorize("SQUARE PAYOUT", 990.0).category == "Business Income"

    def test_zero_amount_never_income(self):
        decision = categorize("RANDOM UNKNOWN STORE", 0.0)
        assert decision.status == STATUS_NEEDS_REVIEW


class TestNeedsReviewPolicy:
    def test_unrecognized_merchant_is_flagged_not_guessing(self):
        decision = categorize("KRUNK'S DISCOUNT MARINA", -77.0)
        assert decision.category == NEEDS_REVIEW_CATEGORY
        assert decision.status == STATUS_NEEDS_REVIEW
        assert "guess" in decision.reason.lower() or decision.rule is None

    def test_empty_description(self):
        decision = categorize("", -10.0)
        assert decision.status == STATUS_NEEDS_REVIEW

    def test_opaque_card_noise(self):
        decision = categorize("POS PURCHASE #88421", -12.5)
        assert decision.status == STATUS_NEEDS_REVIEW
        assert decision.category == NEEDS_REVIEW_CATEGORY

    def test_negative_refund_wording_is_reviewed_as_ambiguous(self):
        # A "refund" that reduces the balance is contradictory; do not guess.
        decision = categorize("REFUND FOR DEFECTIVE ITEM", -40.0)
        assert decision.status == STATUS_NEEDS_REVIEW

    def test_negative_refund_wording_beats_a_matching_merchant_rule(self):
        # The merchant alone would claim the negative amount as a Travel
        # expense; the refund word must stop that guess.
        decision = categorize("UBER TRIP REFUND", -25.0)
        assert decision.status == STATUS_NEEDS_REVIEW
        assert decision.category == NEEDS_REVIEW_CATEGORY
        assert decision.rule == "refund"
        assert categorize("UBER TRIP", -25.0).category == "Travel"


class TestDeterminism:
    def test_same_input_same_output(self):
        runs = {
            (
                categorize("Amazon Web Services *Compute", -84.21).category,
                categorize("Amazon Web Services *Compute", -84.21).status,
                categorize("Amazon Web Services *Compute", -84.21).rule,
            )
            for _ in range(25)
        }
        assert len(runs) == 1

    def test_categories_exposed_to_ui_are_valid(self):
        for description, amount in [
            ("UBER", -1.0),
            ("CLIENT PAYMENT", 1.0),
            ("MYSTERY", -1.0),
        ]:
            assert categorize(description, amount).category in ALL_CATEGORIES


class TestDuplicateDetection:
    def test_identical_rows_map_to_first_occurrence(self):
        from app.engine.brain import find_duplicate_pairs

        rows = [
            ("2026-01-05", "UBER TRIP", -23.4),
            ("2026-01-05", "uber  trip", -23.4),  # normalizes identically
            ("2026-01-06", "UBER TRIP", -23.4),   # different date
        ]
        assert find_duplicate_pairs(rows) == {1: 0}

    def test_refund_reason_links_to_original_expense_category(self):
        decision = categorize("Adobe Creative Cloud", 54.99)
        assert decision.category == "Refund / Credit"
        assert "Software & Subscriptions" in decision.reason


class TestNoLLMConstraint:
    """brain.py must not import or call any AI/LLM library (critical constraint)."""

    FORBIDDEN = {
        "openai",
        "anthropic",
        "google.generativeai",
        "langchain",
        "llama",
        "transformers",
        "torch",
        "tensorflow",
        "sklearn",
        "mistralai",
        "cohere",
    }

    def test_brain_has_no_ai_imports(self):
        source = Path(__file__).resolve().parents[1] / "app" / "engine" / "brain.py"
        tree = ast.parse(source.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported & self.FORBIDDEN


class TestDesignerUseCase:
    """The chosen customer: a freelance designer on a business card."""

    @pytest.mark.parametrize("description,amount,category,rule", [
        ("ADOBE CREATIVE CLOUD FULL PLAN", -54.99, "Software & Subscriptions", "software"),
        ("PROCREATE IPAD", -12.99, "Software & Subscriptions", "software"),
        ("FIGMA PROFESSIONAL", -15.00, "Software & Subscriptions", "software"),
        ("WACOM PEN DISPLAY 2", -399.00, "Office & Equipment", "office"),
        ("COPIC MARKER SET 72", -189.00, "Office & Equipment", "office"),
        ("SHUTTLE ART FINE ART PRINTS", -64.40, "Marketing & Advertising", "design_assets"),
        ("VISTAPRINT BUSINESS CARDS", -79.00, "Marketing & Advertising", "design_assets"),
        ("MYFONTS FONT LICENSE", -18.00, "Marketing & Advertising", "design_assets"),
        ("CONFERENCE TICKET DOMAIN OF THINGS", -340.0, "Professional Services", "professional"),
        ("99DESIGNS PAYOUT", 850.00, "Business Income", "payout"),
        ("INVOICE 2026-14 ACME DESIGN STUDIO", 1200.00, "Business Income", "client_income"),
    ])
    def test_persona_merchants(self, description, amount, category, rule):
        decision = categorize(description, amount)
        assert (decision.category, decision.rule, decision.status) == (category, rule, "Reviewed")

    def test_specific_asset_phrase_beats_generic_merchant_token(self):
        # "adobe stock" is an asset purchase; plain "adobe" is a tool. Order in
        # RULES is the documented precedence, and this pins it down.
        assert categorize("ADOBE STOCK ASSET PURCHASE", -29.99).category == "Marketing & Advertising"
        assert categorize("ADOBE CREATIVE CLOUD", -54.99).category == "Software & Subscriptions"

    def test_card_payment_to_own_credit_account_is_not_an_expense(self):
        decision = categorize("PAYMENT TO CHASE SAW 4417", -1200.00)
        assert decision.category == "Transfers & Internal"
        assert decision.rule == "transfers"

    def test_interest_charged_is_a_bank_fee_not_a_purchase(self):
        decision = categorize("INTEREST CHARGED ON OUTSTANDING BALANCE", -14.20)
        assert decision.category == "Banking & Finance Fees"

    def test_zelle_friends_and_family_is_internal_not_business_spending(self):
        decision = categorize("ZELLE JANE FRIENDS AND FAMILY", -60.00)
        assert decision.category == "Transfers & Internal"


class TestDisputeSignals:
    def test_chargeback_debit_is_flagged_not_categorized(self):
        # The merchant text describes the disputed purchase, so guessing the
        # category from it would be wrong.
        decision = categorize("DISPUTE - UBER TRIP AIRPORT", -38.20)
        assert decision.status == "Needs Review"
        assert decision.category == "Uncategorized"
        assert "dispute" in decision.reason.lower()

    def test_chargeback_fee_is_a_real_bank_fee(self):
        assert categorize("CHARGEBACK FEE", -25.00).category == "Banking & Finance Fees"

    def test_dispute_credit_still_lands_in_refunds_not_income(self):
        decision = categorize("DISPUTE WON CHARGEBACK CREDIT", 38.20)
        assert decision.category == "Refund / Credit"
        assert decision.status == "Reviewed"
