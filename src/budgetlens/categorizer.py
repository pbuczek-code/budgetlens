from __future__ import annotations

import re
from typing import Optional

import pandas as pd

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "Groceries": ("market", "grocery", "groceries", "aldi", "lidl", "carrefour", "walmart", "biedronka", "zabka"),
    "Dining": ("restaurant", "cafe", "coffee", "pizza", "burger", "sushi", "lunch", "dinner"),
    "Transport": ("uber", "bolt", "taxi", "fuel", "gas", "metro", "train", "ticket", "parking"),
    "Housing": ("rent", "mortgage", "utilities", "electricity", "water", "internet", "czynsz"),
    "Subscriptions": ("netflix", "spotify", "apple", "google", "subscription", "membership", "cloud"),
    "Shopping": ("amazon", "allegro", "shop", "store", "mall", "electronics", "book"),
    "Health": ("pharmacy", "doctor", "clinic", "medical", "gym", "dentist"),
    "Education": ("course", "school", "university", "book store", "udemy"),
    "Travel": ("hotel", "flight", "airline", "booking", "airbnb"),
    "Income": ("salary", "payroll", "invoice payment", "refund", "client payment"),
}


def categorize_transactions(df: pd.DataFrame, custom_rules: Optional[dict[str, list[str]]] = None) -> pd.DataFrame:
    categorized = df.copy()
    rows = [categorize_with_metadata(row, custom_rules) for _, row in categorized.iterrows()]
    categorized["category"] = [row["category"] for row in rows]
    categorized["category_source"] = [row["source"] for row in rows]
    categorized["category_confidence"] = [row["confidence"] for row in rows]
    return categorized


def categorize_row(row: pd.Series, custom_rules: Optional[dict[str, list[str]]] = None) -> str:
    return categorize_with_metadata(row, custom_rules)["category"]


def categorize_with_metadata(row: pd.Series, custom_rules: Optional[dict[str, list[str]]] = None) -> dict:
    if "source_category" in row and str(row["source_category"]).strip():
        return {"category": str(row["source_category"]).strip(), "source": "provided", "confidence": 1.0}

    if row["amount"] > 0:
        return {"category": "Income", "source": "income", "confidence": 1.0}

    description = str(row["description"]).lower()

    for category, keywords in normalized_custom_rules(custom_rules).items():
        if any(keyword in description for keyword in keywords):
            return {"category": category, "source": "custom", "confidence": 0.95}

    for category, keywords in CATEGORY_RULES.items():
        if any(keyword in description for keyword in keywords):
            return {"category": category, "source": "rule", "confidence": 0.8}

    return {"category": "Other", "source": "fallback", "confidence": 0.35}


def normalized_custom_rules(custom_rules: Optional[dict[str, list[str]]]) -> dict[str, list[str]]:
    if not custom_rules:
        return {}

    cleaned = {}
    for category, keywords in custom_rules.items():
        normalized_keywords = [str(keyword).strip().lower() for keyword in keywords if str(keyword).strip()]
        if normalized_keywords:
            cleaned[str(category).strip()] = normalized_keywords
    return cleaned


def keyword_suggestions(df: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    uncategorized = df[df.get("category", "") == "Other"].copy()
    if uncategorized.empty:
        return pd.DataFrame(columns=["keyword", "transactions", "spending"])

    rows = []
    for _, row in uncategorized.iterrows():
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", str(row["description"]).lower())
        for word in words:
            rows.append({"keyword": word, "amount": abs(float(row["amount"]))})

    if not rows:
        return pd.DataFrame(columns=["keyword", "transactions", "spending"])

    data = pd.DataFrame(rows)
    return (
        data.groupby("keyword", as_index=False)
        .agg(transactions=("keyword", "count"), spending=("amount", "sum"))
        .sort_values(["transactions", "spending"], ascending=[False, False])
        .head(limit)
    )