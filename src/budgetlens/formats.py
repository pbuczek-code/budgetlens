from __future__ import annotations

import pandas as pd

from budgetlens.cleaner import BANK_PRESETS, normalize_column_name


def preset_names() -> list[str]:
    return ["Auto"] + sorted(BANK_PRESETS.keys())


def score_bank_presets(df: pd.DataFrame) -> pd.DataFrame:
    columns = {normalize_column_name(column) for column in df.columns}
    rows = []

    for name, config in BANK_PRESETS.items():
        score = 0
        for group in ("date", "description", "amount", "debit", "credit"):
            candidates = config.get(group, ())
            if any(normalize_column_name(candidate) in columns for candidate in candidates):
                score += 1
        rows.append({"preset": name, "score": score})

    return pd.DataFrame(rows).sort_values(["score", "preset"], ascending=[False, True])


def best_preset(df: pd.DataFrame) -> str:
    scores = score_bank_presets(df)
    if scores.empty or scores.iloc[0]["score"] == 0:
        return "Auto"
    return str(scores.iloc[0]["preset"])