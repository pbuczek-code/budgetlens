from __future__ import annotations

import pandas as pd

DEFAULT_BUDGETS: dict[str, float] = {
    "Groceries": 600.0,
    "Dining": 250.0,
    "Transport": 200.0,
    "Housing": 1500.0,
    "Subscriptions": 100.0,
    "Shopping": 400.0,
    "Health": 200.0,
    "Education": 150.0,
    "Travel": 500.0,
    "Other": 300.0,
}


def monthly_budget_status(df: pd.DataFrame, budgets: dict[str, float]) -> pd.DataFrame:
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["month", "category", "budget", "spent", "remaining", "used_pct", "status"])

    expenses["month"] = expenses["date"].dt.to_period("M").astype(str)
    expenses["spent"] = expenses["amount"].abs()
    monthly = expenses.groupby(["month", "category"], as_index=False).agg(spent=("spent", "sum"))

    months = sorted(expenses["month"].unique())
    rows = []
    for month in months:
        for category, budget in budgets.items():
            if budget <= 0:
                continue
            match = monthly[(monthly["month"] == month) & (monthly["category"] == category)]
            spent = float(match["spent"].sum()) if not match.empty else 0.0
            used_pct = spent / float(budget) if budget else 0.0
            rows.append(
                {
                    "month": month,
                    "category": category,
                    "budget": float(budget),
                    "spent": spent,
                    "remaining": float(budget) - spent,
                    "used_pct": used_pct,
                    "status": budget_status(used_pct),
                }
            )

    return pd.DataFrame(rows)


def budget_status(used_pct: float) -> str:
    if used_pct >= 1.0:
        return "Over budget"
    if used_pct >= 0.85:
        return "Close"
    return "On track"


def current_budget_month(status: pd.DataFrame) -> pd.DataFrame:
    if status.empty:
        return status
    latest_month = str(status["month"].max())
    return status[status["month"] == latest_month].sort_values("used_pct", ascending=False)