import pandas as pd

from budgetlens.cleaner import clean_transactions, parse_amount


def test_parse_amount_handles_common_formats():
    assert parse_amount("$1,200.50") == 1200.50
    assert parse_amount("-45,20") == -45.20
    assert parse_amount("") is None


def test_clean_transactions_normalizes_columns():
    raw = pd.DataFrame(
        {
            "Transaction Date": ["2026-01-02"],
            "Merchant": ["Coffee House"],
            "Amount": ["-8.40"],
        }
    )

    cleaned = clean_transactions(raw)

    assert list(cleaned.columns) == ["date", "description", "amount"]
    assert cleaned.loc[0, "description"] == "Coffee House"
    assert cleaned.loc[0, "amount"] == -8.40
