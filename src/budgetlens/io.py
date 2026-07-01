from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd


def load_transactions(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Load transactions from a CSV path or uploaded file object."""
    return pd.read_csv(source)
