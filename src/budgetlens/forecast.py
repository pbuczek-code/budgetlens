from __future__ import annotations

import calendar

import pandas as pd


def forecast_month_end(df: pd.DataFrame) -> dict:
    if df.empty:
        return empty_forecast()

    max_date = df["date"].max()
    month_start = max_date.replace(day=1)
    days_in_month = calendar.monthrange(max_date.year, max_date.month)[1]
    days_elapsed = max(1, int(max_date.day))
    month_data = df[(df["date"] >= month_start) & (df["date"] <= max_date)].copy()

    spending_so_far = float(month_data[month_data["amount"] < 0]["amount"].abs().sum())
    income_so_far = float(month_data[month_data["amount"] > 0]["amount"].sum())
    projected_spending = spending_so_far / days_elapsed * days_in_month
    projected_net = income_so_far - projected_spending

    return {
        "month": max_date.strftime("%Y-%m"),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "spending_so_far": spending_so_far,
        "income_so_far": income_so_far,
        "projected_spending": projected_spending,
        "projected_net": projected_net,
        "daily_spending_rate": spending_so_far / days_elapsed,
    }


def forecast_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["category", "spent_so_far", "projected_spending"])

    summary = forecast_month_end(df)
    max_date = df["date"].max()
    month_start = max_date.replace(day=1)
    month_data = df[(df["date"] >= month_start) & (df["date"] <= max_date) & (df["amount"] < 0)].copy()
    if month_data.empty:
        return pd.DataFrame(columns=["category", "spent_so_far", "projected_spending"])

    month_data["spent_so_far"] = month_data["amount"].abs()
    grouped = month_data.groupby("category", as_index=False).agg(spent_so_far=("spent_so_far", "sum"))
    grouped["projected_spending"] = grouped["spent_so_far"] / summary["days_elapsed"] * summary["days_in_month"]
    return grouped.sort_values("projected_spending", ascending=False)


def empty_forecast() -> dict:
    return {
        "month": "",
        "days_elapsed": 0,
        "days_in_month": 0,
        "spending_so_far": 0.0,
        "income_so_far": 0.0,
        "projected_spending": 0.0,
        "projected_net": 0.0,
        "daily_spending_rate": 0.0,
    }