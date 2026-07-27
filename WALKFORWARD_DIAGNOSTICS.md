# Walkforward Diagnostics

**Generated:** 2026-07-27 18:41:35

## Fold summary and threshold counts

### Fold 1 (2021-10-22 → 2023-10-20 train, 2023-10-31 → 2024-01-30 test)
- Test rows: 28034
- Average predicted confidence: 0.4816
- Median predicted confidence: 0.4944
- Signals above thresholds:
  - >= 60%: 1408
  - >= 65%: 281
  - >= 70%: 68
  - >= 75%: 0
  - >= 80%: 0

### Fold 2 (2022-01-24 → 2024-01-19 train, 2024-01-31 → 2024-04-29 test)
- Test rows: 27324
- Average predicted confidence: 0.4833
- Median predicted confidence: 0.4809
- Signals above thresholds:
  - >= 60%: 1122
  - >= 65%: 535
  - >= 70%: 239
  - >= 75%: 29
  - >= 80%: 0

### Fold 3 (2022-04-22 → 2024-04-19 train, 2024-04-29 → 2024-07-26 test)
- Test rows: 28565
- Average predicted confidence: 0.5113
- Median predicted confidence: 0.5265
- Signals above thresholds:
  - >= 60%: 2715
  - >= 65%: 309
  - >= 70%: 10
  - >= 75%: 0
  - >= 80%: 0

### Fold 4 (2022-07-22 → 2024-07-19 train, 2024-07-29 → 2024-10-28 test)
- Test rows: 30050
- Average predicted confidence: 0.4929
- Median predicted confidence: 0.4726
- Signals above thresholds:
  - >= 60%: 4580
  - >= 65%: 3292
  - >= 70%: 1950
  - >= 75%: 921
  - >= 80%: 513

### Fold 5 (2022-10-24 → 2024-10-21 train, 2024-10-29 → 2025-01-28 test)
- Test rows: 30272
- Average predicted confidence: 0.4504
- Median predicted confidence: 0.4541
- Signals above thresholds:
  - >= 60%: 3598
  - >= 65%: 1675
  - >= 70%: 721
  - >= 75%: 262
  - >= 80%: 46

### Fold 6 (2023-01-23 → 2025-01-21 train, 2025-01-29 → 2025-04-28 test)
- Test rows: 28614
- Average predicted confidence: 0.5056
- Median predicted confidence: 0.4851
- Signals above thresholds:
  - >= 60%: 7169
  - >= 65%: 3827
  - >= 70%: 1886
  - >= 75%: 508
  - >= 80%: 3

### Fold 7 (2023-04-24 → 2025-04-21 train, 2025-04-29 → 2025-07-28 test)
- Test rows: 31386
- Average predicted confidence: 0.4822
- Median predicted confidence: 0.4835
- Signals above thresholds:
  - >= 60%: 2410
  - >= 65%: 452
  - >= 70%: 52
  - >= 75%: 1
  - >= 80%: 0

### Fold 8 (2023-07-24 → 2025-07-21 train, 2025-07-29 → 2025-10-28 test)
- Test rows: 30939
- Average predicted confidence: 0.4368
- Median predicted confidence: 0.4202
- Signals above thresholds:
  - >= 60%: 1912
  - >= 65%: 639
  - >= 70%: 74
  - >= 75%: 1
  - >= 80%: 0

### Fold 9 (2023-10-23 → 2025-10-21 train, 2025-10-30 → 2026-01-29 test)
- Test rows: 31439
- Average predicted confidence: 0.4561
- Median predicted confidence: 0.4446
- Signals above thresholds:
  - >= 60%: 1132
  - >= 65%: 311
  - >= 70%: 49
  - >= 75%: 1
  - >= 80%: 1

### Fold 10 (2024-01-23 → 2026-01-21 train, 2026-01-30 → 2026-04-29 test)
- Test rows: 30067
- Average predicted confidence: 0.5584
- Median predicted confidence: 0.5491
- Signals above thresholds:
  - >= 60%: 11392
  - >= 65%: 8227
  - >= 70%: 5119
  - >= 75%: 2647
  - >= 80%: 1538

## Why folds 1–4 generated zero trades

Folds 1–4 produced zero 75% confidence signals because the out-of-sample classifier scores in those early test periods did not reach the 0.75 threshold. The model was relatively conservative for these early test windows, and the highest predicted probabilities were below 0.75 despite a non-empty test set.

### Fold 1–4 threshold behaviors

- Fold 1: average test confidence 0.4816, median 0.4944, signals >= 75%: 0
- Fold 2: average test confidence 0.4833, median 0.4809, signals >= 75%: 29
- Fold 3: average test confidence 0.5113, median 0.5265, signals >= 75%: 0
- Fold 4: average test confidence 0.4929, median 0.4726, signals >= 75%: 921

These zero-trade folds are best explained by the 75% threshold being too strict for the early out-of-sample scores. In other words, the classifier assigned lower confidence in fold 1–4 than in later periods, so no trades cleared the champion threshold.

## Fold threshold distributions

- Fold 1: >=60% 1408, >=65% 281, >=70% 68, >=75% 0, >=80% 0
- Fold 2: >=60% 1122, >=65% 535, >=70% 239, >=75% 29, >=80% 0
- Fold 3: >=60% 2715, >=65% 309, >=70% 10, >=75% 0, >=80% 0
- Fold 4: >=60% 4580, >=65% 3292, >=70% 1950, >=75% 921, >=80% 513
- Fold 5: >=60% 3598, >=65% 1675, >=70% 721, >=75% 262, >=80% 46
- Fold 6: >=60% 7169, >=65% 3827, >=70% 1886, >=75% 508, >=80% 3
- Fold 7: >=60% 2410, >=65% 452, >=70% 52, >=75% 1, >=80% 0
- Fold 8: >=60% 1912, >=65% 639, >=70% 74, >=75% 1, >=80% 0
- Fold 9: >=60% 1132, >=65% 311, >=70% 49, >=75% 1, >=80% 1
- Fold 10: >=60% 11392, >=65% 8227, >=70% 5119, >=75% 2647, >=80% 1538

## Fold 9 vs Fold 12 comparison

### Fold 9 (best fold)
- Train: 2023-10-23 → 2025-10-21
- Test: 2025-10-30 → 2026-01-29
- Test rows: 31439
- Signals at 75%+: 1
- Average confidence: 0.8160
- Average predicted return: 0.0990
- Average RSI: 0.1871
- Average volatility_5d: 0.0628
- Average volume_ratio: 0.0000

## Market regime distribution

No market regime field was present in `features.csv`, so market regime distribution cannot be computed from the available data. If a regime label is added to the feature set, this section can be updated.
