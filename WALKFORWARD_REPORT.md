# Walk-Forward Validation Report

**Generated:** 2026-06-03 11:02:16

## Summary

- Total folds considered: **12**
- Folds with trades: **8**
- Strategy threshold: **75%**
- Train window: **24 months**
- Test window: **3 months**
- Gap between train/test: **5 trading days**

## Fold metrics

| Fold | Train | Test | Trades | Win Rate % | Prediction Success % | Portfolio Return % | Max Drawdown % |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 2021-03-15 → 2023-03-14 | 2023-03-22 → 2023-06-21 | 0 | nan | nan | nan | nan |
| 2 | 2021-06-15 → 2023-06-14 | 2023-06-22 → 2023-09-21 | 0 | nan | nan | nan | nan |
| 3 | 2021-09-15 → 2023-09-14 | 2023-09-25 → 2023-12-22 | 0 | nan | nan | nan | nan |
| 4 | 2021-12-15 → 2023-12-14 | 2023-12-22 → 2024-03-21 | 0 | nan | nan | nan | nan |
| 5 | 2022-03-15 → 2024-03-14 | 2024-03-22 → 2024-06-21 | 1 | 100.00 | 100.00 | 0.79 | -0.03 |
| 6 | 2022-06-15 → 2024-06-14 | 2024-06-25 → 2024-09-24 | 68 | 55.88 | 64.71 | 6.83 | -1.58 |
| 7 | 2022-09-15 → 2024-09-13 | 2024-09-23 → 2024-12-20 | 343 | 63.56 | 58.31 | 6.32 | -4.64 |
| 8 | 2022-12-15 → 2024-12-13 | 2024-12-23 → 2025-03-21 | 230 | 49.57 | 57.83 | 7.01 | -9.37 |
| 9 | 2023-03-15 → 2025-03-13 | 2025-03-24 → 2025-06-23 | 38 | 84.21 | 81.58 | 22.16 | -2.16 |
| 10 | 2023-06-15 → 2025-06-13 | 2025-06-23 → 2025-09-22 | 1 | 100.00 | 100.00 | 0.13 | -0.27 |
| 11 | 2023-09-15 → 2025-09-12 | 2025-09-22 → 2025-12-19 | 7 | 57.14 | 57.14 | 0.33 | -1.81 |
| 12 | 2023-12-15 → 2025-12-12 | 2025-12-22 → 2026-03-20 | 449 | 22.05 | 50.33 | -3.75 | -11.64 |

## Average metrics

- Average trade count: **94.8**
- Average win rate: **66.55%**
- Average prediction success rate: **71.24%**
- Average portfolio return: **4.98%**
- Average max drawdown: **-3.94%**

## Standard deviation

- Trade count stddev: **156.8**
- Win rate stddev: **26.81%**
- Prediction success stddev: **19.95%**
- Portfolio return stddev: **7.96%**
- Max drawdown stddev: **4.33%**

## Best fold

- Fold **9**: 2023-03-15 → 2025-03-13 train, 2025-03-24 → 2025-06-23 test
- Portfolio return: **22.16%**
- Win rate: **84.21%**
- Prediction success: **81.58%**
- Max drawdown: **-2.16%**

## Worst fold

- Fold **12**: 2023-12-15 → 2025-12-12 train, 2025-12-22 → 2026-03-20 test
- Portfolio return: **-3.75%**
- Win rate: **22.05%**
- Prediction success: **50.33%**
- Max drawdown: **-11.64%**

## Overall assessment

This walk-forward validation evaluates the champion-style strategy on rolling, out-of-sample test windows with a realistic 5-day hold period and 5-trading-day separation from training data. The results above show how stable the strategy is across quarterly retraining folds, and identify whether the model generalizes consistently or suffers from fold-specific drawdowns.

## Output files

- `walkforward_results.csv`
- `WALKFORWARD_REPORT.md`

## Notes

- This validation pipeline is separate from the champion strategy. It uses the same model configuration and portfolio simulator logic but operates on rolling train/test folds.
- Folds with zero trades are included for transparency; their performance metrics are recorded as missing values.