import pandas as pd

from budgetlens.categorizer import categorize_transactions


def test_categorizes_known_expense():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01"]),
            "description": ["Lidl groceries"],
            "amount": [-25.0],
        }
    )

    result = categorize_transactions(df)

    assert result.loc[0, "category"] == "Groceries"


def test_positive_amount_is_income():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01"]),
            "description": ["Salary"],
            "amount": [4000.0],
        }
    )

    result = categorize_transactions(df)

    assert result.loc[0, "category"] == "Income"
