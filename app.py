from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.express as px
import streamlit as st

from budgetlens.analytics import (
    category_summary,
    detect_unusual_expenses,
    monthly_summary,
    savings_kpis,
    savings_summary,
    top_expenses,
)
from budgetlens.budgets import DEFAULT_BUDGETS, current_budget_month, monthly_budget_status
from budgetlens.categorizer import categorize_transactions, keyword_suggestions
from budgetlens.cleaner import clean_transactions
from budgetlens.exports import dataframe_to_csv_bytes, dataframe_to_json_bytes, summary_bundle_to_json_bytes
from budgetlens.forecast import forecast_by_category, forecast_month_end
from budgetlens.formats import preset_names, score_bank_presets
from budgetlens.io import load_transactions
from budgetlens.privacy import mask_transactions
from budgetlens.reports import generate_pdf_report
from budgetlens.subscriptions import detect_subscriptions

DEMO_DATA = ROOT / "data" / "demo_transactions.csv"

st.set_page_config(page_title="BudgetLens", page_icon="BL", layout="wide")


def load_raw(source) -> pd.DataFrame:
    if hasattr(source, "seek"):
        source.seek(0)
    return load_transactions(source)


def prepare_data(source, preset: str, custom_rules: dict[str, list[str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_raw(source)
    cleaned = clean_transactions(raw, preset=preset)
    categorized = categorize_transactions(cleaned, custom_rules=custom_rules)
    return raw, categorized


def money(value: float) -> str:
    return f"${value:,.2f}"


def get_custom_rules() -> dict[str, list[str]]:
    if "custom_rules" not in st.session_state:
        st.session_state.custom_rules = {}
    return st.session_state.custom_rules


def add_custom_rule(category: str, keyword: str) -> None:
    keyword = keyword.strip().lower()
    category = category.strip()
    if not keyword or not category:
        return
    rules = get_custom_rules()
    rules.setdefault(category, [])
    if keyword not in rules[category]:
        rules[category].append(keyword)
    st.session_state.custom_rules = rules


def apply_transaction_filters(
    df: pd.DataFrame,
    query: str,
    categories: list[str],
    date_range,
    amount_range: tuple[float, float],
) -> pd.DataFrame:
    filtered = df.copy()

    if query:
        filtered = filtered[filtered["description"].str.contains(query, case=False, na=False)]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered = filtered[(filtered["date"] >= start_date) & (filtered["date"] <= end_date)]

    min_amount, max_amount = amount_range
    filtered = filtered[(filtered["amount"] >= min_amount) & (filtered["amount"] <= max_amount)]
    return filtered


def display_frame(df: pd.DataFrame, privacy_enabled: bool, round_amounts: bool) -> pd.DataFrame:
    if privacy_enabled:
        return mask_transactions(df, mask_merchants=True, round_amounts=round_amounts)
    return df


st.title("BudgetLens")
st.caption("Personal finance analytics for CSV bank exports.")

sample_files = sorted((ROOT / "data").glob("*.csv"))
if not sample_files:
    sample_files = [DEMO_DATA]

with st.sidebar:
    st.header("Data")
    uploaded_file = st.file_uploader("Upload transactions CSV", type=["csv"])
    use_sample = st.toggle("Use sample data", value=uploaded_file is None)
    selected_sample = st.selectbox("Sample CSV", sample_files, format_func=lambda path: path.name)
    bank_preset = st.selectbox("Bank format", preset_names())

    st.header("Privacy")
    privacy_enabled = st.toggle("Presentation privacy mode", value=False)
    round_private_amounts = st.toggle("Round displayed amounts", value=False, disabled=not privacy_enabled)

    st.header("Category rules")
    custom_category = st.selectbox("Rule category", sorted(DEFAULT_BUDGETS.keys()))
    custom_keyword = st.text_input("Description keyword")
    if st.button("Add rule"):
        add_custom_rule(custom_category, custom_keyword)
        st.rerun()

    custom_rules = get_custom_rules()
    if custom_rules:
        st.write(custom_rules)

source = uploaded_file if uploaded_file is not None and not use_sample else selected_sample

try:
    raw_transactions, transactions = prepare_data(source, bank_preset, get_custom_rules())
except Exception as exc:
    st.error(f"Could not load transactions: {exc}")
    st.stop()

expenses = transactions[transactions["amount"] < 0].copy()
income = transactions[transactions["amount"] > 0].copy()
monthly_data = monthly_summary(transactions)
category_data = category_summary(transactions)
unusual_data = detect_unusual_expenses(transactions)
subscription_data = detect_subscriptions(transactions)
forecast_data = forecast_month_end(transactions)
forecast_categories = forecast_by_category(transactions)
savings_data = savings_summary(transactions)
savings_metrics = savings_kpis(transactions)

all_budget_categories = sorted(set(DEFAULT_BUDGETS).union(set(transactions["category"].unique())))

metric_top = st.columns(2)
metric_bottom = st.columns(2)
metric_top[0].metric("Income", money(float(income["amount"].sum())))
metric_top[1].metric("Spending", money(float(abs(expenses["amount"].sum()))))
metric_bottom[0].metric("Net cashflow", money(float(transactions["amount"].sum())))
metric_bottom[1].metric("Transactions", f"{len(transactions):,}")

tabs = st.tabs(
    [
        "Overview",
        "Search",
        "Budgets",
        "Subscriptions",
        "Forecast",
        "Savings",
        "Exports",
        "Data quality",
    ]
)

with tabs[0]:
    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.subheader("Monthly cashflow")
        if monthly_data.empty:
            st.info("No monthly data available.")
        else:
            fig = px.bar(
                monthly_data,
                x="month",
                y=["income", "spending", "net"],
                barmode="group",
                labels={"value": "Amount", "month": "Month", "variable": "Metric"},
            )
            st.plotly_chart(fig, width="stretch")

    with chart_cols[1]:
        st.subheader("Spending by category")
        if category_data.empty:
            st.info("No expense categories available.")
        else:
            fig = px.pie(category_data, values="spending", names="category", hole=0.42)
            st.plotly_chart(fig, width="stretch")

    st.subheader("Top expenses")
    st.dataframe(display_frame(top_expenses(transactions, limit=10), privacy_enabled, round_private_amounts), width="stretch")

with tabs[1]:
    filter_cols = st.columns([2, 2, 2])
    query = filter_cols[0].text_input("Search description")
    selected_categories = filter_cols[1].multiselect(
        "Categories",
        sorted(transactions["category"].unique()),
        default=sorted(transactions["category"].unique()),
    )

    min_date = transactions["date"].min().date()
    max_date = transactions["date"].max().date()
    date_range = filter_cols[2].date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    amount_min = float(transactions["amount"].min())
    amount_max = float(transactions["amount"].max())
    if amount_min == amount_max:
        amount_range = (amount_min, amount_max)
    else:
        amount_range = st.slider("Amount range", min_value=amount_min, max_value=amount_max, value=(amount_min, amount_max))

    filtered = apply_transaction_filters(transactions, query, selected_categories, date_range, amount_range)
    st.dataframe(display_frame(filtered, privacy_enabled, round_private_amounts), width="stretch")
    st.download_button(
        "Download filtered CSV",
        data=dataframe_to_csv_bytes(display_frame(filtered, privacy_enabled, round_private_amounts)),
        file_name="budgetlens_filtered_transactions.csv",
        mime="text/csv",
    )

with tabs[2]:
    budget_cols = st.columns(2)
    budgets = {}
    for index, category in enumerate(all_budget_categories):
        default_value = float(DEFAULT_BUDGETS.get(category, 250.0))
        budgets[category] = budget_cols[index % 2].number_input(
            f"{category} budget",
            min_value=0.0,
            value=default_value,
            step=25.0,
            key=f"budget_{category}",
        )

    budget_status_all = monthly_budget_status(transactions, budgets)
    budget_status_latest = current_budget_month(budget_status_all)

    if budget_status_latest.empty:
        st.info("No budget data available.")
    else:
        budget_chart = budget_status_latest.copy()
        budget_chart["used_pct_display"] = budget_chart["used_pct"] * 100
        fig = px.bar(
            budget_chart,
            x="category",
            y="used_pct_display",
            color="status",
            labels={"used_pct_display": "Budget used percent", "category": "Category"},
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(budget_status_latest, width="stretch")

with tabs[3]:
    if subscription_data.empty:
        st.info("No recurring payments detected.")
    else:
        sub_cols = st.columns(3)
        sub_cols[0].metric("Detected", f"{len(subscription_data):,}")
        sub_cols[1].metric("Monthly estimate", money(float(subscription_data["median_amount"].sum())))
        sub_cols[2].metric("Highest", money(float(subscription_data["median_amount"].max())))
        st.dataframe(display_frame(subscription_data, privacy_enabled, round_private_amounts), width="stretch")

with tabs[4]:
    forecast_cols = st.columns(4)
    forecast_cols[0].metric("Forecast month", forecast_data["month"])
    forecast_cols[1].metric("Spend so far", money(forecast_data["spending_so_far"]))
    forecast_cols[2].metric("Projected spend", money(forecast_data["projected_spending"]))
    forecast_cols[3].metric("Projected net", money(forecast_data["projected_net"]))

    if forecast_categories.empty:
        st.info("No category forecast available.")
    else:
        fig = px.bar(
            forecast_categories,
            x="category",
            y="projected_spending",
            labels={"projected_spending": "Projected spending", "category": "Category"},
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(forecast_categories, width="stretch")

with tabs[5]:
    savings_cols = st.columns(4)
    savings_cols[0].metric("Average savings rate", f"{savings_metrics['average_savings_rate']:.1%}")
    savings_cols[1].metric("Total saved", money(savings_metrics["total_saved"]))
    savings_cols[2].metric("Best month", savings_metrics["best_month"])
    savings_cols[3].metric("Worst month", savings_metrics["worst_month"])

    if savings_data.empty:
        st.info("No savings data available.")
    else:
        fig = px.line(
            savings_data,
            x="month",
            y=["income", "spending", "net"],
            markers=True,
            labels={"value": "Amount", "month": "Month", "variable": "Metric"},
        )
        st.plotly_chart(fig, width="stretch")
        st.dataframe(savings_data, width="stretch")

with tabs[6]:
    export_frame = display_frame(transactions, privacy_enabled, round_private_amounts)
    budget_status_for_report = current_budget_month(monthly_budget_status(transactions, {category: DEFAULT_BUDGETS.get(category, 250.0) for category in all_budget_categories}))
    pdf_bytes = generate_pdf_report(transactions, budget_status_for_report, subscription_data, forecast_data)

    export_cols = st.columns(2)
    export_cols[0].download_button(
        "Cleaned transactions CSV",
        data=dataframe_to_csv_bytes(export_frame),
        file_name="budgetlens_cleaned_transactions.csv",
        mime="text/csv",
    )
    export_cols[1].download_button(
        "Transactions JSON",
        data=dataframe_to_json_bytes(export_frame),
        file_name="budgetlens_transactions.json",
        mime="application/json",
    )
    export_cols[0].download_button(
        "Monthly summary CSV",
        data=dataframe_to_csv_bytes(monthly_data),
        file_name="budgetlens_monthly_summary.csv",
        mime="text/csv",
    )
    export_cols[1].download_button(
        "Analysis bundle JSON",
        data=summary_bundle_to_json_bytes(monthly=monthly_data, categories=category_data, subscriptions=subscription_data),
        file_name="budgetlens_analysis_bundle.json",
        mime="application/json",
    )
    st.download_button(
        "PDF report",
        data=pdf_bytes,
        file_name="budgetlens_report.pdf",
        mime="application/pdf",
    )

with tabs[7]:
    quality_cols = st.columns(3)
    quality_cols[0].metric("Unusual expenses", f"{len(unusual_data):,}")
    quality_cols[1].metric("Fallback categories", f"{int((transactions['category_source'] == 'fallback').sum()):,}")
    quality_cols[2].metric("Average confidence", f"{transactions['category_confidence'].mean():.0%}")

    st.subheader("Bank format scores")
    st.dataframe(score_bank_presets(raw_transactions), width="stretch")

    st.subheader("Unusual expenses")
    if unusual_data.empty:
        st.success("No unusual expenses found.")
    else:
        st.dataframe(display_frame(unusual_data, privacy_enabled, round_private_amounts), width="stretch")

    st.subheader("Category suggestions")
    suggestions = keyword_suggestions(transactions)
    if suggestions.empty:
        st.success("No uncategorized spending found.")
    else:
        st.dataframe(suggestions, width="stretch")