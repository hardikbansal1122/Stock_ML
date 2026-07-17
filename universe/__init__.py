from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd


def get_universe_path(base_dir: Optional[Path] = None) -> Path:
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
    return Path(base_dir) / "universe" / "universe.csv"


def normalize_ticker(ticker: object) -> str:
    if ticker is None:
        return ""
    cleaned = str(ticker).strip().upper()
    if cleaned.endswith(".NS"):
        cleaned = cleaned[:-3]
    if cleaned.endswith(".BO"):
        cleaned = cleaned[:-3]
    return cleaned


def load_universe(path: Optional[Path] = None) -> pd.DataFrame:
    universe_path = Path(path) if path is not None else get_universe_path()
    if not universe_path.exists():
        raise FileNotFoundError(f"Universe file not found: {universe_path}")

    df = pd.read_csv(universe_path)
    if df.empty:
        return pd.DataFrame(columns=["Ticker"])

    if "Ticker" in df.columns:
        values = df["Ticker"]
    else:
        values = df.iloc[:, 0]

    normalized = [normalize_ticker(value) for value in values if pd.notna(value) and str(value).strip()]
    normalized = list(dict.fromkeys(normalized))
    return pd.DataFrame({"Ticker": normalized})


def get_universe_tickers(path: Optional[Path] = None) -> List[str]:
    universe = load_universe(path)
    return universe["Ticker"].astype(str).tolist()
