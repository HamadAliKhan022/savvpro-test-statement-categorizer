"""StatementIQ Decision Engine ("The Brain").

A strict, deterministic categorization engine for bank/card statements.
Categorization decisions are made ONLY with regular expressions and keyword
matching over a prioritized rule table. No external LLMs or AI models are
used, and none may be introduced into this module.

Decision policy:
- Each transaction's description is normalized, then matched against ordered
  rules; the first rule whose polarity allows the transaction's sign wins.
- An income-polarity "refund" keyword on a negative amount contradicts its
  own sign, so the scan stops there instead of letting a later merchant rule
  claim it.
- Negative amounts are treated as expenses; positive amounts are treated as
  income or refunds/credits.
- If no rule matches, the transaction is NEVER guessed into a category.
  It is flagged "Needs Review" with category "Uncategorized".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal, Optional

Polarity = Literal["expense", "income", "any"]

STATUS_REVIEWED = "Reviewed"
STATUS_NEEDS_REVIEW = "Needs Review"

NEEDS_REVIEW_CATEGORY = "Uncategorized"

# Full category vocabulary exposed to the UI.
INCOME_CATEGORIES = [
    "Business Income",
    "Refund / Credit",
    "Interest Income",
    "Transfers & Internal",
]
EXPENSE_CATEGORIES = [
    "Software & Subscriptions",
    "Office & Equipment",
    "Travel",
    "Meals & Entertainment",
    "Professional Services",
    "Marketing & Advertising",
    "Utilities & Telecom",
    "Rent & Occupancy",
    "Payroll & Contractors",
    "Insurance",
    "Banking & Finance Fees",
    "Personal (Non-Deductible)",
]
ALL_CATEGORIES = [NEEDS_REVIEW_CATEGORY] + INCOME_CATEGORIES + EXPENSE_CATEGORIES

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_MULTI_SPACE = re.compile(r"\s+")
# Descriptions that are just terminal/mask noise carry no categorization signal.
_OPACITY_NOISE = re.compile(
    r"^(pos\s+(?:purchase\s+)?(?:#\d+)?\s*)?"
    r"(?:debit\s+card\s+)?(?:purchase\s+)?"
    r"(?:[#]?\d[\d\s\-]*|visa\s+\d[\d\s\-]*|mc\s+\d[\d\s\-]*|"
    r"\d{4,}[a-z]*)\s*$"
)


# A dispute/chargeback tells us the bank reversed something, not what the
# spending category was; it must never be guessed.
_DISPUTE_SIGNAL = re.compile(r"\b(?:dispute|chargeback|charge off)\b")


def normalize_description(description: str) -> str:
    """Lowercase and strip punctuation so rules can rely on plain tokens."""
    return _MULTI_SPACE.sub(" ", _NON_ALNUM.sub(" ", (description or "").lower())).strip()


@dataclass(frozen=True)
class Rule:
    name: str
    category: str
    pattern: re.Pattern
    polarity: str  # "expense" | "income" | "any"


def _rule(name: str, category: str, keywords: List[str], polarity: str = "any") -> Rule:
    alternatives = "|".join(
        r"\s+".join(re.escape(word) for word in kw.strip().lower().split())
        for kw in keywords
    )
    return Rule(
        name=name,
        category=category,
        pattern=re.compile(r"(?:^|\s)(?:" + alternatives + r")(?:\s|$)"),
        polarity=polarity,
    )


# Ordered, prioritized rule table. More specific merchants come before
# generic terms so that, e.g., "AWS MARKETPLACE" resolves to software
# rather than a generic purchase. First match wins (deterministic).
RULES: List[Rule] = [
    # --- Fee/credit signals that override merchant categories -------------
    _rule("bank_fees", "Banking & Finance Fees", [
        "annual fee", "overdraft", "wire fee", "atm fee", "monthly service fee",
        "account fee", "late fee", "foreign transaction fee", "fx fee",
        "interchange fee", "payment gateway fee", "stripe fee", "square fee",
        "interest charged", "finance charge", "penalty interest",
        "card replacement fee", "cash advance fee", "chargeback fee",
        "dispute fee",
    ]),
    _rule("interest_income", "Interest Income", [
        "interest payment", "interest posted", "interest paid", "dividend",
        "interest income",
    ], polarity="income"),

    # --- Income signals ----------------------------------------------------
    _rule("client_income", "Business Income", [
        "invoice", "client payment", "consulting", "retainer", "freelance",
        "upwork", "toptal", "fiverr", "payment received", "deposit from",
        "ach credit", "direct deposit payroll", "paycheck", "salary",
        "royalty", "licensing fee", "work submitted", "remittance adv",
    ], polarity="income"),
    _rule("payout", "Business Income", [
        "square payout", "paypal payout", "stripe payout", "shopify payout",
        "settlement", "payout",
    ], polarity="income"),

    # --- Refunds/credits: expense merchants paid in the positive -----------
    _rule("refund", "Refund / Credit", [
        "refund", "credit return", "merchandise return", "return deposit",
        "reversal", "chargeback credit", "money back guarantee",
        "billing credit", "statement credit",
    ], polarity="income"),

    # --- Internal movements -------------------------------------------------
    _rule("transfers", "Transfers & Internal", [
        "internal transfer", "transfer from", "transfer to", "zelle", "venmo",
        "cash advance", "balance transfer", "teller deposit", "mobile deposit",
        "atm withdrawal", "atm cash", "friends and family", "paypal friends",
        "own account", "savings transfer", "credit card payment",
        "payment to chase", "payment received for account",
    ], polarity="any"),

    # --- Expense categories -------------------------------------------------
    # Placed before `software` on purpose: "ADOBE STOCK ASSET" is a purchased
    # asset, not a tool subscription, and the more specific phrase must win
    # over the generic "adobe" merchant token.
    _rule("design_assets", "Marketing & Advertising", [
        "adobe stock", "istock", "shutterstock", "getty images", "wirestock",
        "creative market", "creativemarket", "myfonts", "font spring",
        "fontshop", "iconfinder", "videohive", "photodune", "envato elements",
        "stock photo", "stock image", "stock asset", "font license",
        "vistaprint", "sticker app", "printful", "mixbook", "shuttle art",
        "flyer printing", "business cards", "trade show banner",
    ]),
    _rule("software", "Software & Subscriptions", [
        "aws", "amazon web services", "microsoft", "office 365", "google workspace",
        "adobe", "figma", "notion labs", "slack", "zoom", "github", "gitlab",
        "atlassian", "dropbox", "openai", "anthropic", "jetbrains", "docker",
        "vercel", "netlify", "cloudflare", "digitalocean", "heroku", "squarespace",
        "wordpress com", "godaddy", "namecheap", "subscription", "monthly service",
        "netflix", "spotify", "youtube premium", "icloud", "apple.com bill",
        "domain registration", "web hosting",
        # design-tool stack for the freelance-designer use case
        "procreate", "affinity", "sketch app", "blender", "cinema 4d",
        "webflow", "framer", "envato", "typekit", "adobe fonts", "zeplin",
        "invision", "principle", "cavalry", "spline 3d", "artstation",
        "behance", "dribbble",
    ]),
    _rule("office", "Office & Equipment", [
        "staples", "officedepot", "office depot", "best buy", "micro center",
        "printer", "toner", "paper and ink", "furniture", "monoprice", "b&h",
        "bh photo", "hardware store", "home depot", "lowe s", "stationery",
        "equipment", "laptop", "monitor", "keyboard", "headset",
        # studio hardware and materials for the designer use case
        "wacom", "drawing tablet", "pen display", "copic", "pro marker",
        "x acto", "light pad", "cutting mat", "mat board", "archive paper",
        "camera lens", "tripod", "studio light", "backdrop", "calipers",
        "framing", "picture frame", "canvas print", "art supply", "mockup",
    ]),
    _rule("travel", "Travel", [
        "uber", "lyft", "delta", "united airlines", "southwest", "ryanair",
        "airbnb", "booking com", "expedia", "marriott", "hilton", "hotel",
        "airline", "flight", "train ticket", "amtrak", "baggage fee",
        "enterprise rent", "hertz", "parking garage", "toll",
    ]),
    _rule("meals", "Meals & Entertainment", [
        "starbucks", "mcdonald s", "subway", "chipotle", "doordash", "ubereats",
        "grubhub", "restaurant", "cafe", "coffee", "catering", "liquor",
        "bar grill", "fast food", "sweetgreen", "panera", "whole foods",
        "trader joe s", "grocery", "supermarket",
    ]),
    _rule("professional", "Professional Services", [
        "accountant", "cpa", "lawyer", "attorney", "legal", "notary",
        "consultant", "coaching", "certification", "courier", "fedex",
        "ups store", "usps", "shipping label", "postage", "printing",
        "mail boxes plus", "insurance broker",
        "conference ticket", "workshop", "webinar", "trade association",
        "guild membership", "design conference", "adobe max", "domain of things",
    ]),
    _rule("marketing", "Marketing & Advertising", [
        "google ads", "facebook ads", "meta ads", "linkedin ads", "mailchimp",
        "hubspot", "canva", "shutterstock", "getty images", "adwords",
        "advertising", "seo services", "flyer printing", "business cards",
        "leadpages", "hoverboard",
    ]),
    _rule("utilities", "Utilities & Telecom", [
        "verizon", "at t", "t mobile", "comcast", "xfinity", "spectrum",
        "electric", "gas bill", "water bill", "internet service",
        "mobile plan", "phone bill", "utility", "energy bill", "ring",
        "viastream", "fiberlink",
    ]),
    _rule("rent", "Rent & Occupancy", [
        "rent payment", "property management", "storage unit", "coworking",
        "we work", "wework", "office space", "lease payment", "maintenance fee",
        "hoa dues",
    ]),
    _rule("payroll", "Payroll & Contractors", [
        "payroll", "gusto", "adp", "workday", "guarantee payment",
        "contractor payment", "1099 payment", "wages", "employee",
        "benefits payment",
    ], polarity="any"),
    _rule("insurance", "Insurance", [
        "insurance", "geico", "progressive", "allstate", "state farm",
        "liberty mutual", "policy premium", "liability coverage",
        "health insurance", "disability premium",
    ]),
    _rule("personal", "Personal (Non-Deductible)", [
        "gym", "planet fitness", "netflix personal", "personal care",
        "haircut", "salon", "spa", "movie", "cinema", "amusement",
        "video game", "steam", "ebay personal", "target", "wal mart",
        "costco", "amazon personal",
    ]),
]


@dataclass(frozen=True)
class Decision:
    category: str
    status: str
    rule: Optional[str]
    reason: str

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "status": self.status,
            "matched_rule": self.rule,
            "reason": self.reason,
        }


def _polarity_allows(rule: Rule, amount: float) -> bool:
    if rule.polarity == "any":
        return True
    if rule.polarity == "income":
        return amount > 0
    return amount < 0


def categorize(description: str, amount: float) -> Decision:
    """Categorize a single transaction deterministically.

    Returns a Decision; unmatched transactions become "Needs Review"
    rather than a guess.
    """
    normalized = normalize_description(description)
    if not normalized or _OPACITY_NOISE.match(normalized):
        return Decision(
            category=NEEDS_REVIEW_CATEGORY,
            status=STATUS_NEEDS_REVIEW,
            rule=None,
            reason="Description contains no recognizable merchant or keyword signal.",
        )
    # A chargeback/Dispute debit is the bank clawing money back; the merchant
    # text describes the disputed purchase, not this movement. Its "fee"
    # sibling is a genuine bank fee, so it falls through to the rules.
    if amount < 0 and _DISPUTE_SIGNAL.search(normalized) and "fee" not in normalized:
        return Decision(
            category=NEEDS_REVIEW_CATEGORY,
            status=STATUS_NEEDS_REVIEW,
            rule=None,
            reason=(
                "Card dispute/chargeback debit: the merchant text describes the "
                "disputed purchase, not what this money movement is. Flagged "
                "for human review instead of guessing."
            ),
        )
    for rule in RULES:
        if not _polarity_allows(rule, amount):
            # "REFUND" on a negative amount is self-contradictory: the bank took
            # money out while the text says money came back. A later merchant rule
            # would happily claim the sign, so stop here instead of guessing.
            if rule.name == "refund" and rule.pattern.search(normalized):
                return Decision(
                    category=NEEDS_REVIEW_CATEGORY,
                    status=STATUS_NEEDS_REVIEW,
                    rule=rule.name,
                    reason=(
                        "Refund/credit wording on a negative amount: the sign and the "
                        "description contradict each other, so this movement is not "
                        "guessed. Flagged for human review."
                    ),
                )
            continue
        if rule.pattern.search(normalized):
            if amount > 0 and rule.category in EXPENSE_CATEGORIES:
                return Decision(
                    category="Refund / Credit",
                    status=STATUS_REVIEWED,
                    rule=rule.name,
                    reason=(
                        f"Positive amount matched the '{rule.category}' merchant "
                        f"rule '{rule.name}'; recorded as a refund associated with "
                        f"{rule.category}, never as income or an expense."
                    ),
                )
            return Decision(
                category=rule.category,
                status=STATUS_REVIEWED,
                rule=rule.name,
                reason=f"Matched rule '{rule.name}' for {rule.category}.",
            )
    return Decision(
        category=NEEDS_REVIEW_CATEGORY,
        status=STATUS_NEEDS_REVIEW,
        rule=None,
        reason="No deterministic rule matched; flagged for human review instead of guessing.",
    )


def find_duplicate_pairs(rows) -> dict:
    """Deterministically detect duplicate-looking transactions.

    `rows` is a sequence of (date, description, amount) tuples in file
    order. Returns {index: first_matching_index} for every row that repeats
    an earlier row's (date, normalized description, amount). Duplicates are
    flagged for review, never deleted.
    """
    seen: dict = {}
    duplicates: dict = {}
    for index, (date, description, amount) in enumerate(rows):
        key = (date, normalize_description(description), round(float(amount), 2))
        if key in seen:
            duplicates[index] = seen[key]
        else:
            seen[key] = index
    return duplicates
