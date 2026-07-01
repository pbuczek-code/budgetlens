from __future__ import annotations

import pandas as pd


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["month"] = data["date"].dt.to_period("M").astype(str)
    data["income"] = data["amount"].where(data["amount"] > 0, 0)
    data["spending"] = data["amount"].where(data["amount"] < 0, 0).abs()

    return data.groupby("month", as_index=False).agg(
        income=("income", "sum"),
        spending=("spending", "sum"),
        net=("amount", "sum"),
    )


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["category", "spending", "transactions"])
    expenses["spending"] = expenses["amount"].abs()
    return (
        expenses.groupby("category", as_index=False)
        .agg(spending=("spending", "sum"), transactions=("amount", "count"))
        .sort_values("spending", ascending=False)
    )


def top_expenses(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["date", "description", "category", "amount"])
    expenses["spending"] = expenses["amount"].abs()
    return (
        expenses.sort_values("spending", ascending=False)
        .loc[:, ["date", "description", "category", "amount"]]
        .head(limit)
    )


def detect_unusual_expenses(df: pd.DataFrame, multiplier: float = 2.0) -> pd.DataFrame:
    expenses = df[df["amount"] < 0].copy()
    if expenses.empty:
        return pd.DataFrame(columns=["date", "description", "category", "amount"])

    expenses["spending"] = expenses["amount"].abs()
    medians = expenses.groupby("category")["spending"].transform("median")
    unusual = expenses[expenses["spending"] >= medians * multiplier]

    return unusual.sort_values("spending", ascending=False).loc[
        :, ["date", "description", "category", "amount"]
    ]


def savings_summary(df: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly_summary(df)
    if monthly.empty:
        return monthly.assign(savings_rate=[])

    monthly["savings"] = monthly["net"].clip(lower=0)
    monthly["savings_rate"] = monthly.apply(
        lambda row: row["net"] / row["income"] if row["income"] > 0 else 0,
        axis=1,
    )
    return monthly


def savings_kpis(df: pd.DataFrame) -> dict:
    savings = savings_summary(df)
    if savings.empty:
        return {"average_savings_rate": 0.0, "best_month": "", "worst_month": "", "total_saved": 0.0}

    return {
        "average_savings_rate": float(savings["savings_rate"].mean()),
        "best_month": str(savings.sort_values("net", ascending=False).iloc[0]["month"]),
        "worst_month": str(savings.sort_values("net", ascending=True).iloc[0]["month"]),
        "total_saved": float(savings["savings"].sum()),
    }