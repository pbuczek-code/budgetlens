from __future__ import annotations

import re
from typing import Iterable, Optional

import pandas as pd

DATE_CANDIDATES = (
    "date",
    "transaction date",
    "booking date",
    "posted date",
    "operation date",
    "data operacji",
    "data ksiegowania",
    "started date",
    "completed date",
    "created on",
)
DESCRIPTION_CANDIDATES = (
    "description",
    "merchant",
    "details",
    "title",
    "name",
    "reference",
    "counterparty",
    "opis",
    "opis operacji",
    "opis transakcji",
    "tytul",
    "kontrahent",
    "odbiorca",
)
AMOUNT_CANDIDATES = (
    "amount",
    "value",
    "transaction amount",
    "balance change",
    "kwota",
    "source amount",
)
DEBIT_CANDIDATES = (
    "paid out",
    "money out",
    "debit",
    "withdrawal",
    "outflow",
    "obciazenie",
)
CREDIT_CANDIDATES = (
    "paid in",
    "money in",
    "credit",
    "deposit",
    "inflow",
    "uznanie",
)
CATEGORY_CANDIDATES = ("category", "kategoria", "type", "transaction type")

BANK_PRESETS = {
    "Generic": {
        "date": DATE_CANDIDATES,
        "description": DESCRIPTION_CANDIDATES,
        "amount": AMOUNT_CANDIDATES,
        "debit": DEBIT_CANDIDATES,
        "credit": CREDIT_CANDIDATES,
    },
    "PKO BP": {
        "date": ("data operacji", "data waluty", "date"),
        "description": ("opis operacji", "tytul", "odbiorca", "description"),
        "amount": ("kwota", "amount"),
    },
    "mBank": {
        "date": ("data operacji", "data ksiegowania", "date"),
        "description": ("opis transakcji", "kontrahent", "description"),
        "amount": ("kwota", "amount"),
    },
    "ING": {
        "date": ("data transakcji", "data ksiegowania", "date"),
        "description": ("dane kontrahenta", "tytul", "description", "details"),
        "amount": ("kwota transakcji", "kwota", "amount"),
    },
    "Revolut": {
        "date": ("started date", "completed date", "date"),
        "description": ("description", "merchant", "reference"),
        "amount": ("amount", "paid in", "paid out"),
        "debit": ("paid out", "money out"),
        "credit": ("paid in", "money in"),
    },
    "Wise": {
        "date": ("created on", "date"),
        "description": ("description", "target name", "reference"),
        "amount": ("amount", "source amount"),
        "debit": ("source amount", "debit"),
        "credit": ("target amount", "credit"),
    },
    "Split debit credit": {
        "date": DATE_CANDIDATES,
        "description": DESCRIPTION_CANDIDATES,
        "debit": DEBIT_CANDIDATES,
        "credit": CREDIT_CANDIDATES,
    },
}


def clean_transactions(df: pd.DataFrame, preset: str = "Auto") -> pd.DataFrame:
    """Normalize transaction exports into date, description, and amount columns."""
    if df.empty:
        raise ValueError("The CSV file is empty.")

    normalized = df.copy()
    normalized.columns = [normalize_column_name(column) for column in normalized.columns]

    config = preset_config(preset)
    date_col = find_column(normalized, config.get("date", DATE_CANDIDATES))
    description_col = find_column(normalized, config.get("description", DESCRIPTION_CANDIDATES))
    amount_series = resolve_amount_series(normalized, config)
    category_col = try_find_column(normalized, CATEGORY_CANDIDATES)

    cleaned = pd.DataFrame(
        {
            "date": pd.to_datetime(normalized[date_col], errors="coerce"),
            "description": normalized[description_col].fillna("").astype(str).str.strip(),
            "amount": amount_series,
        }
    )

    if category_col is not None:
        cleaned["source_category"] = normalized[category_col].fillna("").astype(str).str.strip()

    cleaned = cleaned.dropna(subset=["date", "amount"])
    cleaned = cleaned[cleaned["description"] != ""]
    cleaned = cleaned.sort_values("date").reset_index(drop=True)

    if cleaned.empty:
        raise ValueError("No valid transactions were found after cleaning.")

    return cleaned


def preset_config(preset: str) -> dict:
    if preset != "Auto" and preset in BANK_PRESETS:
        selected = dict(BANK_PRESETS[preset])
        selected["date"] = tuple(selected.get("date", ())) + DATE_CANDIDATES
        selected["description"] = tuple(selected.get("description", ())) + DESCRIPTION_CANDIDATES
        selected["amount"] = tuple(selected.get("amount", ())) + AMOUNT_CANDIDATES
        selected["debit"] = tuple(selected.get("debit", ())) + DEBIT_CANDIDATES
        selected["credit"] = tuple(selected.get("credit", ())) + CREDIT_CANDIDATES
        return selected

    return {
        "date": DATE_CANDIDATES,
        "description": DESCRIPTION_CANDIDATES,
        "amount": AMOUNT_CANDIDATES,
        "debit": DEBIT_CANDIDATES,
        "credit": CREDIT_CANDIDATES,
    }


def normalize_column_name(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def find_column(df: pd.DataFrame, candidates: Iterable[str]) -> str:
    column = try_find_column(df, candidates)
    if column is None:
        raise ValueError(f"Missing required column. Tried: {', '.join(candidates)}")
    return column


def try_find_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    columns = list(df.columns)
    normalized_candidates = tuple(normalize_column_name(candidate) for candidate in candidates)

    for candidate in normalized_candidates:
        if candidate in columns:
            return candidate

    for column in columns:
        if any(candidate in column for candidate in normalized_candidates):
            return column

    return None


def resolve_amount_series(df: pd.DataFrame, config: dict) -> pd.Series:
    debit_col = try_find_column(df, config.get("debit", DEBIT_CANDIDATES))
    credit_col = try_find_column(df, config.get("credit", CREDIT_CANDIDATES))

    if debit_col is not None or credit_col is not None:
        debit = parse_series(df[debit_col]) if debit_col is not None else pd.Series(0, index=df.index)
        credit = parse_series(df[credit_col]) if credit_col is not None else pd.Series(0, index=df.index)
        debit = debit.fillna(0).abs()
        credit = credit.fillna(0).abs()
        combined = credit - debit
        if combined.abs().sum() > 0:
            return combined

    amount_col = find_column(df, config.get("amount", AMOUNT_CANDIDATES))
    return parse_series(df[amount_col])


def parse_series(series: pd.Series) -> pd.Series:
    return series.apply(parse_amount)


def parse_amount(value: object) -> Optional[float]:
    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if text == "":
        return None

    negative_parentheses = text.startswith("(") and text.endswith(")")
    text = text.replace("(", "").replace(")", "")
    text = text.replace("$", "").replace("EUR", "").replace("USD", "").replace("PLN", "")
    text = text.replace("zl", "").replace(" ", "").strip()

    if "," in text and "." in text:
        text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        parsed = float(text)
    except ValueError:
        return None

    return -abs(parsed) if negative_parentheses else parsed