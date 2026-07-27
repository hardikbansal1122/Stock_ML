# Walk-Forward Validation Report

**Generated:** 2026-07-27 18:08:59

## Summary

- Total folds considered: **12**
- Folds with trades: **7**
- Strategy threshold: **75%**
- Train window: **24 months**
- Test window: **3 months**
- Gap between train/test: **6 trading days**

## Fold metrics

| Fold | Train | Test | Trades | Win Rate % | Prediction Success % | Portfolio Return % | Max Drawdown % |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | 2021-03-31 → 2023-03-29 | 2023-04-12 → 2023-07-11 | 0 | nan | nan | nan | nan |
| 2 | 2021-06-30 → 2023-06-28 | 2023-07-10 → 2023-10-09 | 0 | nan | nan | nan | nan |
| 3 | 2021-09-30 → 2023-09-29 | 2023-10-11 → 2024-01-10 | 0 | nan | nan | nan | nan |
| 4 | 2021-12-30 → 2023-12-29 | 2024-01-09 → 2024-04-08 | 0 | nan | nan | nan | nan |
| 5 | 2022-03-30 → 2024-03-28 | 2024-04-09 → 2024-07-08 | 2 | 100.00 | 100.00 | 2.03 | -0.34 |
| 6 | 2022-06-30 → 2024-06-28 | 2024-07-09 → 2024-10-08 | 736 | 70.79 | 71.33 | 13.44 | -1.17 |
| 7 | 2022-09-30 → 2024-09-27 | 2024-10-09 → 2025-01-08 | 272 | 45.22 | 45.59 | -3.27 | -7.98 |
| 8 | 2022-12-30 → 2024-12-27 | 2025-01-07 → 2025-04-04 | 1121 | 53.08 | 66.99 | -8.06 | -16.61 |
| 9 | 2023-03-30 → 2025-03-28 | 2025-04-09 → 2025-07-08 | 13 | 69.23 | 92.31 | 2.38 | -2.29 |
| 10 | 2023-06-30 → 2025-06-27 | 2025-07-08 → 2025-10-07 | 6 | 66.67 | 66.67 | 2.14 | -0.11 |
| 11 | 2023-09-30 → 2025-09-29 | 2025-10-09 → 2026-01-08 | 0 | nan | nan | nan | nan |
| 12 | 2023-12-30 → 2025-12-29 | 2026-01-07 → 2026-04-06 | 1945 | 28.02 | 54.19 | 2.23 | -8.10 |

## Average metrics

- Average trade count: **341.2**
- Average win rate: **61.86%**
- Average prediction success rate: **71.01%**
- Average portfolio return: **1.56%**
- Average max drawdown: **-5.23%**

## Standard deviation

- Trade count stddev: **622.2**
- Win rate stddev: **22.77%**
- Prediction success stddev: **19.40%**
- Portfolio return stddev: **6.57%**
- Max drawdown stddev: **6.06%**

## Best fold

- Fold **6**: 2022-06-30 → 2024-06-28 train, 2024-07-09 → 2024-10-08 test
- Portfolio return: **13.44%**
- Win rate: **70.79%**
- Prediction success: **71.33%**
- Max drawdown: **-1.17%**

## Worst fold

- Fold **8**: 2022-12-30 → 2024-12-27 train, 2025-01-07 → 2025-04-04 test
- Portfolio return: **-8.06%**
- Win rate: **53.08%**
- Prediction success: **66.99%**
- Max drawdown: **-16.61%**

## Overall assessment

This walk-forward validation evaluates the champion-style strategy on rolling, out-of-sample test windows with a realistic 5-day hold period and 5-trading-day separation from training data. The results above show how stable the strategy is across quarterly retraining folds, and identify whether the model generalizes consistently or suffers from fold-specific drawdowns.

## Output files

- `walkforward_results.csv`
- `WALKFORWARD_REPORT.md`

## Notes

- This validation pipeline is separate from the champion strategy. It uses the same model configuration and portfolio simulator logic but operates on rolling train/test folds.
- Folds with zero trades are included for transparency; their performance metrics are recorded as missing values.