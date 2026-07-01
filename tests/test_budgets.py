import pandas as pd

from budgetlens.budgets import current_budget_month, monthly_budget_status


def test_monthly_budget_status_flags_over_budget():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "description": ["Groceries", "More groceries"],
            "amount": [-80.0, -40.0],
            "category": ["Groceries", "Groceries"],
        }
    )

    status = monthly_budget_status(df, {"Groceries": 100.0})

    assert status.loc[0, "spent"] == 120.0
    assert status.loc[0, "status"] == "Over budget"


def test_current_budget_month_returns_latest_month():
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-02-02"]),
            "description": ["Groceries", "Groceries"],
            "amount": [-20.0, -30.0],
            "category": ["Groceries", "Groceries"],
        }
    )

    status = monthly_budget_status(df, {"Groceries": 100.0})
    latest = current_budget_month(status)

    assert latest["month"].unique().tolist() == ["2026-02"]