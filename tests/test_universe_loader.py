from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from step1_download_data import load_universe, normalize_ticker


def test_load_universe_reads_csv_and_normalizes_tickers():
    universe = load_universe(ROOT / 'universe' / 'universe.csv')
    assert not universe.empty
    assert 'Ticker' in universe.columns
    assert universe['Ticker'].astype(str).str.strip().str.len().gt(0).all()
    assert normalize_ticker('RELIANCE') == 'RELIANCE'
    assert normalize_ticker('reliance') == 'RELIANCE'
