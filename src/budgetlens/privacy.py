from __future__ import annotations

import hashlib

import pandas as pd

TEXT_COLUMNS_TO_MASK = ("description", "merchant", "name", "counterparty")
AMOUNT_COLUMNS_TO_ROUND = ("amount", "median_amount", "spending", "spent", "budget", "remaining", "projected_spending")


def mask_transactions(df: pd.DataFrame, mask_merchants: bool = True, round_amounts: bool = False) -> pd.DataFrame:
    masked = df.copy()

    if mask_merchants:
        for column in TEXT_COLUMNS_TO_MASK:
            if column in masked:
                labels = {}
                for value in masked[column].astype(str).unique():
                    labels[value] = masked_label(value)
                masked[column] = masked[column].astype(str).map(labels)

    if round_amounts:
        for column in AMOUNT_COLUMNS_TO_ROUND:
            if column in masked:
                masked[column] = masked[column].apply(round_private_amount)

    return masked


def masked_label(value: object) -> str:
    digest = hashlib.sha1(str(value).lower().encode("utf-8")).hexdigest()[:6]
    return f"Merchant {digest.upper()}"


def round_private_amount(value: float) -> float:
    if pd.isna(value):
        return value
    sign = -1 if value < 0 else 1
    return float(sign * round(abs(float(value)) / 5.0) * 5.0)