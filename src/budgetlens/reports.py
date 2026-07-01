from __future__ import annotations

import textwrap

import pandas as pd

from budgetlens.analytics import category_summary, monthly_summary, top_expenses


def generate_pdf_report(df: pd.DataFrame, budget_status: pd.DataFrame, subscriptions: pd.DataFrame, forecast: dict) -> bytes:
    lines = build_report_lines(df, budget_status, subscriptions, forecast)
    return simple_pdf("BudgetLens monthly report", lines)


def build_report_lines(df: pd.DataFrame, budget_status: pd.DataFrame, subscriptions: pd.DataFrame, forecast: dict) -> list[str]:
    month_data = monthly_summary(df)
    category_data = category_summary(df)
    top_data = top_expenses(df, limit=5)

    lines = ["BudgetLens monthly report", ""]
    if not month_data.empty:
        latest = month_data.iloc[-1]
        lines.extend(
            [
                f"Latest month: {latest['month']}",
                f"Income: ${latest['income']:,.2f}",
                f"Spending: ${latest['spending']:,.2f}",
                f"Net cashflow: ${latest['net']:,.2f}",
                "",
            ]
        )

    if forecast:
        lines.extend(
            [
                f"Projected spending for {forecast.get('month', '')}: ${forecast.get('projected_spending', 0):,.2f}",
                f"Projected net cashflow: ${forecast.get('projected_net', 0):,.2f}",
                "",
            ]
        )

    lines.append("Top categories")
    for _, row in category_data.head(6).iterrows():
        lines.append(f"- {row['category']}: ${row['spending']:,.2f}")

    lines.extend(["", "Top expenses"])
    for _, row in top_data.iterrows():
        lines.append(f"- {row['date'].date()} {row['description']}: ${abs(row['amount']):,.2f}")

    if not budget_status.empty:
        lines.extend(["", "Budget watch"])
        for _, row in budget_status.head(6).iterrows():
            lines.append(f"- {row['category']}: {row['status']} at {row['used_pct']:.0%}")

    if not subscriptions.empty:
        lines.extend(["", "Detected subscriptions"])
        for _, row in subscriptions.head(6).iterrows():
            lines.append(f"- {row['merchant']}: about ${row['median_amount']:,.2f}")

    return lines


def simple_pdf(title: str, lines: list[str]) -> bytes:
    content_lines = []
    y_step = 16
    content_lines.append("BT")
    content_lines.append("/F1 18 Tf")
    content_lines.append("50 790 Td")
    content_lines.append(f"({escape_pdf(title)}) Tj")
    content_lines.append("/F1 10 Tf")
    content_lines.append(f"0 -{y_step * 2} Td")

    wrapped = []
    for line in lines:
        if line == "":
            wrapped.append("")
        else:
            wrapped.extend(textwrap.wrap(str(line), width=92) or [""])

    for line in wrapped[:44]:
        content_lines.append(f"({escape_pdf(line)}) Tj")
        content_lines.append(f"0 -{y_step} Td")

    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("ascii"))
    return bytes(pdf)


def escape_pdf(text: object) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")