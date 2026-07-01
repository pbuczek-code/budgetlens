import pandas as pd

from budgetlens.analytics import category_summary, detect_unusual_expenses, monthly_summary


def test_monthly_summary_splits_income_and_spending():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "description": ["Salary", "Groceries"],
            "amount": [1000.0, -100.0],
            "category": ["Income", "Groceries"],
        }
    )

    result = monthly_summary(df)

    assert result.loc[0, "income"] == 1000.0
    assert result.loc[0, "spending"] == 100.0
    assert result.loc[0, "net"] == 900.0


def test_category_summary_uses_expenses_only():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "description": ["Salary", "Groceries"],
            "amount": [1000.0, -100.0],
            "category": ["Income", "Groceries"],
        }
    )

    result = category_summary(df)

    assert result.loc[0, "category"] == "Groceries"
    assert result.loc[0, "spending"] == 100.0


def test_detect_unusual_expenses_flags_large_category_outlier():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "description": ["Small grocery", "Normal grocery", "Large grocery"],
            "amount": [-10.0, -12.0, -60.0],
            "category": ["Groceries", "Groceries", "Groceries"],
        }
    )

    result = detect_unusual_expenses(df, multiplier=2.0)

    assert "Large grocery" in result["description"].tolist()
