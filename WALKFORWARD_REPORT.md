# Walk-Forward Validation Report

**Generated:** 2026-06-03 10:41:07

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
| 5 | 2022-03-15 → 2024-03-14 | 2024-03-22 → 2024-06-21 | 2 | 100.00 | 100.00 | 0.84 | -0.40 |
| 6 | 2022-06-15 → 2024-06-14 | 2024-06-25 → 2024-09-24 | 72 | 52.78 | 63.89 | 4.57 | -1.03 |
| 7 | 2022-09-15 → 2024-09-13 | 2024-09-23 → 2024-12-20 | 337 | 63.80 | 60.24 | 6.57 | -3.20 |
| 8 | 2022-12-15 → 2024-12-13 | 2024-12-23 → 2025-03-21 | 224 | 50.45 | 60.27 | 2.03 | -9.34 |
| 9 | 2023-03-15 → 2025-03-13 | 2025-03-24 → 2025-06-23 | 42 | 85.71 | 83.33 | 23.29 | -2.49 |
| 10 | 2023-06-15 → 2025-06-13 | 2025-06-23 → 2025-09-22 | 2 | 100.00 | 100.00 | 0.85 | -0.37 |
| 11 | 2023-09-15 → 2025-09-12 | 2025-09-22 → 2025-12-19 | 3 | 66.67 | 66.67 | 0.51 | -1.49 |
| 12 | 2023-12-15 → 2025-12-12 | 2025-12-22 → 2026-03-20 | 430 | 21.40 | 53.02 | -0.72 | -9.54 |

## Average metrics

- Average trade count: **92.7**
- Average win rate: **67.60%**
- Average prediction success rate: **73.43%**
- Average portfolio return: **4.74%**
- Average max drawdown: **-3.48%**

## Standard deviation

- Trade count stddev: **151.5**
- Win rate stddev: **26.97%**
- Prediction success stddev: **18.56%**
- Portfolio return stddev: **7.86%**
- Max drawdown stddev: **3.80%**

## Best fold

- Fold **9**: 2023-03-15 → 2025-03-13 train, 2025-03-24 → 2025-06-23 test
- Portfolio return: **23.29%**
- Win rate: **85.71%**
- Prediction success: **83.33%**
- Max drawdown: **-2.49%**

## Worst fold

- Fold **12**: 2023-12-15 → 2025-12-12 train, 2025-12-22 → 2026-03-20 test
- Portfolio return: **-0.72%**
- Win rate: **21.40%**
- Prediction success: **53.02%**
- Max drawdown: **-9.54%**

## Overall assessment

This walk-forward validation evaluates the champion-style strategy on rolling, out-of-sample test windows with a realistic 5-day hold period and 5-trading-day separation from training data. The results above show how stable the strategy is across quarterly retraining folds, and identify whether the model generalizes consistently or suffers from fold-specific drawdowns.

## Output files

- `walkforward_results.csv`
- `WALKFORWARD_REPORT.md`

## Notes

- This validation pipeline is separate from the champion strategy. It uses the same model configuration and portfolio simulator logic but operates on rolling train/test folds.
- Folds with zero trades are included for transparency; their performance metrics are recorded as missing values.