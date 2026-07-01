import pandas as pd

from budgetlens.forecast import forecast_by_category, forecast_month_end
from budgetlens.privacy import mask_transactions
from budgetlens.reports import generate_pdf_report
from budgetlens.subscriptions import detect_subscriptions


def sample_transactions():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-05", "2026-02-05", "2026-03-05", "2026-03-20"]),
            "description": ["Netflix subscription", "Netflix subscription", "Netflix subscription", "Aldi groceries"],
            "amount": [-15.0, -15.0, -15.0, -80.0],
            "category": ["Subscriptions", "Subscriptions", "Subscriptions", "Groceries"],
        }
    )


def test_detect_subscriptions_finds_recurring_payment():
    result = detect_subscriptions(sample_transactions())

    assert not result.empty
    assert result.iloc[0]["occurrences"] == 3


def test_forecast_month_end_projects_spending():
    result = forecast_month_end(sample_transactions())

    assert result["month"] == "2026-03"
    assert result["projected_spending"] > result["spending_so_far"]


def test_forecast_by_category_returns_categories():
    result = forecast_by_category(sample_transactions())

    assert "Groceries" in result["category"].tolist()


def test_privacy_masks_merchants_and_rounds_amounts():
    masked = mask_transactions(sample_transactions(), round_amounts=True)

    assert masked.loc[0, "description"].startswith("Merchant ")
    assert masked.loc[0, "amount"] == -15.0


def test_pdf_report_generates_pdf_bytes():
    df = sample_transactions()
    pdf = generate_pdf_report(df, pd.DataFrame(), pd.DataFrame(), forecast_month_end(df))

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500