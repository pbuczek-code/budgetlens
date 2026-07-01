from __future__ import annotations

import json
from io import StringIO

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def dataframe_to_json_bytes(df: pd.DataFrame) -> bytes:
    text = df.to_json(orient="records", date_format="iso", indent=2)
    return text.encode("utf-8")


def summary_bundle_to_json_bytes(**frames: pd.DataFrame) -> bytes:
    payload = {}
    for name, frame in frames.items():
        payload[name] = json.loads(frame.to_json(orient="records", date_format="iso"))
    return json.dumps(payload, indent=2).encode("utf-8")