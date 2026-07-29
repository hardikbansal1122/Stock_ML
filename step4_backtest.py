#!/usr/bin/env python3
"""STEP 4: Backtest entry point.
This script now delegates all logic to the reusable orchestration layer.
"""

from portfolio_pipeline import run_pipeline

if __name__ == "__main__":
    run_pipeline()
