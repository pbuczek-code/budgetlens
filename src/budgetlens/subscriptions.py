from __future__ import annotations

import re

import pandas as pd


def detect_subscriptions(df: pd.DataFrame, min_occurrences: int = 2, amount_tolerance: float = 0.30) -> pd.DataFrame:
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame(columns=subscription_columns())

    expenses["merchant_key"] = expenses["description"].apply(normalize_merchant)
    expenses["spending"] = expenses["amount"].abs()
    rows = []

    for merchant_key, group in expenses.groupby("merchant_key"):
        group = group.sort_values("date")
        if len(group) < min_occurrences:
            continue

        median_amount = float(group["spending"].median())
        if median_amount == 0:
            continue

        max_deviation = float((group["spending"] - median_amount).abs().max() / median_amount)
        gaps = group["date"].diff().dt.days.dropna()
        median_gap = float(gaps.median()) if not gaps.empty else 30.0
        category = str(group["category"].mode().iloc[0]) if "category" in group else "Other"
        is_recurring_gap = 20 <= median_gap <= 45 or len(group) >= 3
        is_stable_amount = max_deviation <= amount_tolerance
        known_recurring = category in ("Subscriptions", "Housing")

        if not (is_recurring_gap and (is_stable_amount or known_recurring)):
            continue

        rows.append(
            {
                "merchant": str(group["description"].iloc[-1]),
                "category": category,
                "occurrences": int(len(group)),
                "median_amount": median_amount,
                "last_seen": group["date"].max(),
                "median_gap_days": median_gap,
                "next_expected": group["date"].max() + pd.Timedelta(days=int(round(median_gap))),
                "confidence": subscription_confidence(len(group), max_deviation, known_recurring),
            }
        )

    if not rows:
        return pd.DataFrame(columns=subscription_columns())

    return pd.DataFrame(rows).sort_values(["confidence", "median_amount"], ascending=[False, False])


def normalize_merchant(description: object) -> str:
    text = str(description).lower()
    text = re.sub(r"\b\d{2,}\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    words = [word for word in text.split() if word not in {"payment", "purchase", "card", "pos"}]
    return " ".join(words[:3]) or "unknown"


def subscription_confidence(count: int, deviation: float, known_recurring: bool) -> float:
    score = 0.45
    score += min(count, 4) * 0.1
    score += max(0.0, 0.25 - deviation)
    if known_recurring:
        score += 0.15
    return round(min(score, 0.98), 2)


def subscription_columns() -> list[str]:
    return ["merchant", "category", "occurrences", "median_amount", "last_seen", "median_gap_days", "next_expected", "confidence"]