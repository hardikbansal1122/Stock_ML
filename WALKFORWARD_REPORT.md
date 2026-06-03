# Walk-Forward Validation Report

**Generated:** 2026-06-03 10:22:50

## Summary

- Total folds considered: **12**
- Folds with trades: **7**
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
| 5 | 2022-03-15 → 2024-03-14 | 2024-03-22 → 2024-06-21 | 0 | nan | nan | nan | nan |
| 6 | 2022-06-15 → 2024-06-14 | 2024-06-25 → 2024-09-24 | 59 | 50.85 | 62.71 | 7.25 | -1.23 |
| 7 | 2022-09-15 → 2024-09-13 | 2024-09-23 → 2024-12-20 | 417 | 60.67 | 56.35 | 5.40 | -2.49 |
| 8 | 2022-12-15 → 2024-12-13 | 2024-12-23 → 2025-03-21 | 234 | 49.15 | 58.97 | 7.79 | -9.07 |
| 9 | 2023-03-15 → 2025-03-13 | 2025-03-24 → 2025-06-23 | 49 | 87.76 | 83.67 | 23.28 | -1.87 |
| 10 | 2023-06-15 → 2025-06-13 | 2025-06-23 → 2025-09-22 | 3 | 66.67 | 100.00 | 0.62 | -0.71 |
| 11 | 2023-09-15 → 2025-09-12 | 2025-09-22 → 2025-12-19 | 3 | 100.00 | 66.67 | 1.05 | -0.43 |
| 12 | 2023-12-15 → 2025-12-12 | 2025-12-22 → 2026-03-20 | 400 | 19.25 | 52.25 | -1.43 | -10.68 |

## Average metrics

- Average trade count: **97.1**
- Average win rate: **62.05%**
- Average prediction success rate: **68.66%**
- Average portfolio return: **6.28%**
- Average max drawdown: **-3.78%**

## Standard deviation

- Trade count stddev: **160.0**
- Win rate stddev: **26.61%**
- Prediction success stddev: **17.13%**
- Portfolio return stddev: **8.29%**
- Max drawdown stddev: **4.25%**

## Best fold

- Fold **9**: 2023-03-15 → 2025-03-13 train, 2025-03-24 → 2025-06-23 test
- Portfolio return: **23.28%**
- Win rate: **87.76%**
- Prediction success: **83.67%**
- Max drawdown: **-1.87%**

## Worst fold

- Fold **12**: 2023-12-15 → 2025-12-12 train, 2025-12-22 → 2026-03-20 test
- Portfolio return: **-1.43%**
- Win rate: **19.25%**
- Prediction success: **52.25%**
- Max drawdown: **-10.68%**

## Overall assessment

This walk-forward validation evaluates the champion-style strategy on rolling, out-of-sample test windows with a realistic 5-day hold period and 5-trading-day separation from training data. The results above show how stable the strategy is across quarterly retraining folds, and identify whether the model generalizes consistently or suffers from fold-specific drawdowns.

## Output files

- `walkforward_results.csv`
- `WALKFORWARD_REPORT.md`

## Notes

- This validation pipeline is separate from the champion strategy. It uses the same model configuration and portfolio simulator logic but operates on rolling train/test folds.
- Folds with zero trades are included for transparency; their performance metrics are recorded as missing values.