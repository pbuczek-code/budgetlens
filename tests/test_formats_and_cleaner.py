import pandas as pd

from budgetlens.cleaner import clean_transactions
from budgetlens.formats import best_preset, score_bank_presets


def test_clean_transactions_supports_split_debit_credit_columns():
    raw = pd.DataFrame(
        {
            "Date": ["2026-01-01", "2026-01-02"],
            "Description": ["Salary", "Groceries"],
            "Money In": ["1000.00", ""],
            "Money Out": ["", "45.50"],
        }
    )

    cleaned = clean_transactions(raw, preset="Split debit credit")

    assert cleaned.loc[0, "amount"] == 1000.0
    assert cleaned.loc[1, "amount"] == -45.5


def test_clean_transactions_keeps_provided_category():
    raw = pd.DataFrame(
        {
            "Date": ["2026-01-01"],
            "Description": ["Coffee"],
            "Amount": ["-4.50"],
            "Category": ["Dining"],
        }
    )

    cleaned = clean_transactions(raw)

    assert cleaned.loc[0, "source_category"] == "Dining"


def test_bank_preset_scoring_returns_best_match():
    raw = pd.DataFrame(
        {
            "Started Date": ["2026-01-01"],
            "Description": ["Coffee"],
            "Amount": ["-4.50"],
        }
    )

    scores = score_bank_presets(raw)

    assert not scores.empty
    assert best_preset(raw) in scores["preset"].tolist()