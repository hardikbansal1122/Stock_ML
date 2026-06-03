# Walkforward Diagnostics

**Generated:** 2026-06-02 19:39:21

## Fold summary and threshold counts

### Fold 1 (2021-03-15 → 2023-03-14 train, 2023-03-22 → 2023-06-21 test)
- Test rows: 11100
- Average predicted confidence: 0.4876
- Median predicted confidence: 0.4972
- Signals above thresholds:
  - >= 60%: 404
  - >= 65%: 34
  - >= 70%: 2
  - >= 75%: 0
  - >= 80%: 0

### Fold 2 (2021-06-15 → 2023-06-14 train, 2023-06-22 → 2023-09-21 test)
- Test rows: 11513
- Average predicted confidence: 0.4725
- Median predicted confidence: 0.4818
- Signals above thresholds:
  - >= 60%: 316
  - >= 65%: 5
  - >= 70%: 0
  - >= 75%: 0
  - >= 80%: 0

### Fold 3 (2021-09-15 → 2023-09-14 train, 2023-09-25 → 2023-12-22 test)
- Test rows: 11208
- Average predicted confidence: 0.4527
- Median predicted confidence: 0.4473
- Signals above thresholds:
  - >= 60%: 463
  - >= 65%: 95
  - >= 70%: 4
  - >= 75%: 0
  - >= 80%: 0

### Fold 4 (2021-12-15 → 2023-12-14 train, 2023-12-22 → 2024-03-21 test)
- Test rows: 11223
- Average predicted confidence: 0.4908
- Median predicted confidence: 0.4976
- Signals above thresholds:
  - >= 60%: 542
  - >= 65%: 45
  - >= 70%: 1
  - >= 75%: 0
  - >= 80%: 0

### Fold 5 (2022-03-15 → 2024-03-14 train, 2024-03-22 → 2024-06-21 test)
- Test rows: 10856
- Average predicted confidence: 0.4801
- Median predicted confidence: 0.4713
- Signals above thresholds:
  - >= 60%: 1171
  - >= 65%: 278
  - >= 70%: 24
  - >= 75%: 3
  - >= 80%: 0

### Fold 6 (2022-06-15 → 2024-06-14 train, 2024-06-25 → 2024-09-24 test)
- Test rows: 11774
- Average predicted confidence: 0.4970
- Median predicted confidence: 0.4869
- Signals above thresholds:
  - >= 60%: 1736
  - >= 65%: 577
  - >= 70%: 232
  - >= 75%: 93
  - >= 80%: 10

### Fold 7 (2022-09-15 → 2024-09-13 train, 2024-09-23 → 2024-12-20 test)
- Test rows: 11404
- Average predicted confidence: 0.5052
- Median predicted confidence: 0.4957
- Signals above thresholds:
  - >= 60%: 1861
  - >= 65%: 1005
  - >= 70%: 573
  - >= 75%: 339
  - >= 80%: 192

### Fold 8 (2022-12-15 → 2024-12-13 train, 2024-12-23 → 2025-03-21 test)
- Test rows: 11592
- Average predicted confidence: 0.5075
- Median predicted confidence: 0.4986
- Signals above thresholds:
  - >= 60%: 2611
  - >= 65%: 1568
  - >= 70%: 766
  - >= 75%: 236
  - >= 80%: 59

### Fold 9 (2023-03-15 → 2025-03-13 train, 2025-03-24 → 2025-06-23 test)
- Test rows: 11223
- Average predicted confidence: 0.5018
- Median predicted confidence: 0.4883
- Signals above thresholds:
  - >= 60%: 1810
  - >= 65%: 769
  - >= 70%: 218
  - >= 75%: 40
  - >= 80%: 2

### Fold 10 (2023-06-15 → 2025-06-13 train, 2025-06-23 → 2025-09-22 test)
- Test rows: 11776
- Average predicted confidence: 0.4419
- Median predicted confidence: 0.4335
- Signals above thresholds:
  - >= 60%: 364
  - >= 65%: 84
  - >= 70%: 14
  - >= 75%: 2
  - >= 80%: 0

### Fold 11 (2023-09-15 → 2025-09-12 train, 2025-09-22 → 2025-12-19 test)
- Test rows: 11408
- Average predicted confidence: 0.4391
- Median predicted confidence: 0.4327
- Signals above thresholds:
  - >= 60%: 257
  - >= 65%: 88
  - >= 70%: 34
  - >= 75%: 11
  - >= 80%: 0

### Fold 12 (2023-12-15 → 2025-12-12 train, 2025-12-22 → 2026-03-20 test)
- Test rows: 11224
- Average predicted confidence: 0.5105
- Median predicted confidence: 0.4893
- Signals above thresholds:
  - >= 60%: 2579
  - >= 65%: 1722
  - >= 70%: 1005
  - >= 75%: 458
  - >= 80%: 211

## Why folds 1–4 generated zero trades

Folds 1–4 produced zero 75% confidence signals because the out-of-sample classifier scores in those early test periods did not reach the 0.75 threshold. The model was relatively conservative for these early test windows, and the highest predicted probabilities were below 0.75 despite a non-empty test set.

### Fold 1–4 threshold behaviors

- Fold 1: average test confidence 0.4876, median 0.4972, signals >= 75%: 0
- Fold 2: average test confidence 0.4725, median 0.4818, signals >= 75%: 0
- Fold 3: average test confidence 0.4527, median 0.4473, signals >= 75%: 0
- Fold 4: average test confidence 0.4908, median 0.4976, signals >= 75%: 0

These zero-trade folds are best explained by the 75% threshold being too strict for the early out-of-sample scores. In other words, the classifier assigned lower confidence in fold 1–4 than in later periods, so no trades cleared the champion threshold.

## Fold threshold distributions

- Fold 1: >=60% 404, >=65% 34, >=70% 2, >=75% 0, >=80% 0
- Fold 2: >=60% 316, >=65% 5, >=70% 0, >=75% 0, >=80% 0
- Fold 3: >=60% 463, >=65% 95, >=70% 4, >=75% 0, >=80% 0
- Fold 4: >=60% 542, >=65% 45, >=70% 1, >=75% 0, >=80% 0
- Fold 5: >=60% 1171, >=65% 278, >=70% 24, >=75% 3, >=80% 0
- Fold 6: >=60% 1736, >=65% 577, >=70% 232, >=75% 93, >=80% 10
- Fold 7: >=60% 1861, >=65% 1005, >=70% 573, >=75% 339, >=80% 192
- Fold 8: >=60% 2611, >=65% 1568, >=70% 766, >=75% 236, >=80% 59
- Fold 9: >=60% 1810, >=65% 769, >=70% 218, >=75% 40, >=80% 2
- Fold 10: >=60% 364, >=65% 84, >=70% 14, >=75% 2, >=80% 0
- Fold 11: >=60% 257, >=65% 88, >=70% 34, >=75% 11, >=80% 0
- Fold 12: >=60% 2579, >=65% 1722, >=70% 1005, >=75% 458, >=80% 211

## Fold 9 vs Fold 12 comparison

### Fold 9 (best fold)
- Train: 2023-03-15 → 2025-03-13
- Test: 2025-03-24 → 2025-06-23
- Test rows: 11223
- Signals at 75%+: 40
- Average confidence: 0.7735
- Average predicted return: 0.0799
- Average RSI: -0.0041
- Average volatility_5d: 0.0387
- Average volume_ratio: 1.4097

### Fold 12 (worst fold)
- Train: 2023-12-15 → 2025-12-12
- Test: 2025-12-22 → 2026-03-20
- Test rows: 11224
- Signals at 75%+: 458
- Average confidence: 0.8101
- Average predicted return: -0.0228
- Average RSI: -0.2805
- Average volatility_5d: 0.0250
- Average volume_ratio: 1.1441

## Market regime distribution

No market regime field was present in `features.csv`, so market regime distribution cannot be computed from the available data. If a regime label is added to the feature set, this section can be updated.
