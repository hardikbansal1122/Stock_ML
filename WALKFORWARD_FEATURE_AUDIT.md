# Walkforward Feature Audit

Date: 2026-06-03

## Summary

- `walkforward_validation.py` uses a `FEATURE_COLS` list containing 23 features for model training.
- `step3_train_model.py` uses a `FEATURE_COLS` list containing 26 features.
- `relative_volume` is not included in `walkforward_validation.py`.
- `rs_ret_5d` and `rs_ret_20d` are not included in `walkforward_validation.py`.
- The walk-forward pipeline does not use the same feature set as `step3_train_model.py`.

## Feature lists used for training

### `step3_train_model.py`
- Features count: 26
- Feature list:
  - ret_1d
  - ret_3d
  - ret_5d
  - ret_10d
  - ret_20d
  - price_vs_ma5
  - price_vs_ma20
  - price_vs_ma50
  - ma5_vs_ma20
  - ma10_vs_ma50
  - rsi_normalized
  - volatility_5d
  - volatility_20d
  - hl_range
  - volume_ratio
  - volume_trend
  - relative_volume
  - bb_position
  - up_days_5
  - up_days_10
  - gap
  - nifty_ret_5d
  - nifty_ret_20d
  - nifty_above_ma50
  - rs_ret_5d
  - rs_ret_20d

### `walkforward_validation.py`
- Features count: 23
- Feature list:
  - ret_1d
  - ret_3d
  - ret_5d
  - ret_10d
  - ret_20d
  - price_vs_ma5
  - price_vs_ma20
  - price_vs_ma50
  - ma5_vs_ma20
  - ma10_vs_ma50
  - rsi_normalized
  - volatility_5d
  - volatility_20d
  - hl_range
  - volume_ratio
  - volume_trend
  - bb_position
  - up_days_5
  - up_days_10
  - gap
  - nifty_ret_5d
  - nifty_ret_20d
  - nifty_above_ma50

## Audit questions

1. What feature list is used for training?
   - `walkforward_validation.py` uses its own `FEATURE_COLS` constant defined near the top of the file.
2. How many features are passed into XGBoost?
   - 23 features.
3. Is `relative_volume` included?
   - No.
4. Are `rs_ret_5d` and `rs_ret_20d` included?
   - No, neither is included.
5. Does the walk-forward pipeline use the same feature set as `step3_train_model.py`?
   - No. `walkforward_validation.py` is missing these features compared to `step3_train_model.py`.

## Missing features in `walkforward_validation.py`

- `relative_volume`
- `rs_ret_5d`
- `rs_ret_20d`

## Notes

- `walkforward_validation.py` still uses `nifty_ret_5d`, `nifty_ret_20d`, and `nifty_above_ma50`, but omits the newer relative-volume and relative-strength fields that `step3_train_model.py` includes.
- If the goal is feature set parity between production training and walk-forward validation, these missing fields should be added to `walkforward_validation.py`.
