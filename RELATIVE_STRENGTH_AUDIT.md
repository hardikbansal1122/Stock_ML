# Relative Strength Feature Audit

Date: 2026-06-02

Summary
- `rs_ret_5d`: Present in `features.csv`.
- `rs_ret_20d`: Present in `features.csv`.
- Both features are fully populated (no nulls) across `features.csv` rows.
- `step3_train_model.py` does NOT include `rs_ret_5d` or `rs_ret_20d` in `FEATURE_COLS`, and they are therefore not passed to XGBoost.
- Feature importance for these two fields: Not applicable (not used in training).

Dataset summary
- Total rows in `features.csv`: 228,960
- Unique tickers: 184
- Date range: 2021-03-15 -> 2026-05-21

Detailed stats

- rs_ret_5d
  - Present: yes
  - Non-null: 228,960 / 228,960 (100.0%)
  - Mean: 0.002004084674778044
  - Std: 0.04574742695113176
  - Min: -0.6235854215367492
  - Max: 0.9011351866967352

- rs_ret_20d
  - Present: yes
  - Non-null: 228,960 / 228,960 (100.0%)
  - Mean: 0.008200313475261773
  - Std: 0.09406384270711597
  - Min: -0.7112417616021802
  - Max: 1.584420573209179

Inspection of training pipeline
- File inspected: `step3_train_model.py` (workspace root)
- `FEATURE_COLS` in that script includes: returns, MA features, RSI, volatility, volume, `nifty_ret_5d`, `nifty_ret_20d`, and `nifty_above_ma50`.
- `rs_ret_5d` and `rs_ret_20d` are NOT listed in `FEATURE_COLS` and therefore are not selected into `X_train` / `X_test`.
- XGBoost is trained on `X_train` built from `FEATURE_COLS`, so relative-strength features were not passed into XGBoost during the last recorded training run.

Feature importance
- Since the RS features are not part of `FEATURE_COLS`, no feature importance values exist for them in `xgb_model.pkl` produced by the training script.

Notes & next steps (optional)
- If you want `rs_ret_5d`/`rs_ret_20d` evaluated by the model, add them to `FEATURE_COLS` in `step3_train_model.py` (and re-run training).  Example insertion point is alongside the other return and nifty features.
- After re-training, inspect `xg.feature_importances_` (the script already prints and saves `feature_list.csv`) to get importance values and quantify impact.

End of audit.
