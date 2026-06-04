#!/usr/bin/env python3
"""
STEP 3: Train and validate XGBoost model.
Time-based split — no data leakage.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

print("="*65)
print(" STEP 3: Training ML Model")
print("="*65)

# ── Load features ────────────────────────────────────────────────────────
df = pd.read_csv('features.csv')
df['Date'] = pd.to_datetime(df['Date'])
print(f"\n Loaded {len(df):,} rows from {df['ticker'].nunique()} stocks")

FEATURE_COLS = [
    'ret_1d','ret_3d','ret_5d','ret_10d','ret_20d',
    'price_vs_ma5','price_vs_ma20','price_vs_ma50',
    'ma5_vs_ma20','ma10_vs_ma50',
    'rsi_normalized',
    'volatility_5d','volatility_20d','hl_range',
    'volume_ratio','volume_trend','relative_volume','updown_vol_ratio_10',
    'bb_position',
    'up_days_5','up_days_10',
    'gap',
    'nifty_ret_5d','nifty_ret_20d','nifty_above_ma50',
    'rs_ret_5d','rs_ret_20d',
    'cs_rank_20d'  # ← Cross-sectional momentum rank
]

print("Relative Strength features enabled:\nrs_ret_5d\nrs_ret_20d")

# ── Time-based train/test split ──────────────────────────────────────────
# Train on: 2021-01-01 to 2024-06-30
# Test on : 2024-07-01 onwards  (genuinely unseen)
SPLIT_DATE = '2024-07-01'

train = df[df['Date'] < SPLIT_DATE].dropna(subset=FEATURE_COLS)
test  = df[df['Date'] >= SPLIT_DATE].dropna(subset=FEATURE_COLS)

X_train = train[FEATURE_COLS]
y_train = train['target']
X_test  = test[FEATURE_COLS]
y_test  = test['target']

print(f"\n Train: {len(train):,} rows ({train['Date'].min().date()} -> {train['Date'].max().date()})")
print(f" Test : {len(test):,} rows  ({test['Date'].min().date()} -> {test['Date'].max().date()})")
print(f" Features: {len(FEATURE_COLS)}")
print(f" Target base rate (train): {y_train.mean()*100:.1f}%")
print(f" Target base rate (test) : {y_test.mean()*100:.1f}%")

# ── Model 1: Logistic Regression (baseline) ──────────────────────────────
print("\n[1] Logistic Regression...")
scaler   = StandardScaler()
X_tr_s   = scaler.fit_transform(X_train)
X_te_s   = scaler.transform(X_test)

lr = LogisticRegression(max_iter=1000, C=0.1)
lr.fit(X_tr_s, y_train)
lr_pred  = lr.predict(X_te_s)
lr_proba = lr.predict_proba(X_te_s)[:,1]
lr_acc   = accuracy_score(y_test, lr_pred)
lr_prec  = precision_score(y_test, lr_pred, zero_division=0)
lr_auc   = roc_auc_score(y_test, lr_proba)

print(f"   Accuracy  : {lr_acc*100:.1f}%")
print(f"   Precision : {lr_prec*100:.1f}%  (of predicted positives, how many were right?)")
print(f"   ROC-AUC   : {lr_auc:.3f}  (0.5 = random, 1.0 = perfect)")

# ── Model 2: XGBoost ─────────────────────────────────────────────────────
print("\n[2] XGBoost...")
scale_pos = (y_train==0).sum() / (y_train==1).sum()

xg = xgb.XGBClassifier(
    n_estimators   = 300,
    max_depth      = 4,
    learning_rate  = 0.03,
    subsample      = 0.8,
    colsample_bytree = 0.8,
    scale_pos_weight = scale_pos,
    objective      = 'binary:logistic',
    eval_metric    = 'auc',
    random_state   = 42,
    n_jobs         = -1
)
xg.fit(X_train, y_train,
       eval_set=[(X_test, y_test)],
       verbose=False)

xg_proba = xg.predict_proba(X_test)[:,1]

# Use 60% confidence threshold (only act when model is sure)
threshold   = 0.60
xg_pred_thr = (xg_proba >= threshold).astype(int)

xg_acc   = accuracy_score(y_test, xg_proba >= 0.5)
xg_prec  = precision_score(y_test, xg_pred_thr, zero_division=0)
xg_auc   = roc_auc_score(y_test, xg_proba)
xg_signals = xg_pred_thr.sum()

# ── Model 3: XGBoost regression for 5-day net return ───────────────
y_train_reg = train['ret_5d_net']
y_test_reg  = test['ret_5d_net']

xg_reg = xgb.XGBRegressor(
    n_estimators   = 200,
    max_depth      = 4,
    learning_rate  = 0.03,
    subsample      = 0.8,
    colsample_bytree = 0.8,
    objective      = 'reg:squarederror',
    random_state   = 42,
    n_jobs         = -1
)
xg_reg.fit(X_train, y_train_reg,
          eval_set=[(X_test, y_test_reg)],
          verbose=False)

pred_return = xg_reg.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test_reg, pred_return))
print(f"\n   Regression RMSE: {rmse:.4f}")

print(f"   Accuracy  : {xg_acc*100:.1f}%  (at 0.5 threshold)")
print(f"   Precision : {xg_prec*100:.1f}%  (at 0.6 threshold — high confidence only)")
print(f"   ROC-AUC   : {xg_auc:.3f}")
print(f"   Signals   : {xg_signals:,} / {len(y_test):,} days ({xg_signals/len(y_test)*100:.1f}% of all)")

# ── Feature importance ───────────────────────────────────────────────────
print("\n[3] Top 10 features by importance:")
fi = pd.DataFrame({
    'Feature':    FEATURE_COLS,
    'Importance': xg.feature_importances_
}).sort_values('Importance', ascending=False)

for _, r in fi.head(10).iterrows():
    bar = '#' * int(r['Importance'] * 200)
    print(f"   {r['Feature']:>18} {r['Importance']:.3f} {bar}")

# ── Precision at different confidence levels ──────────────────────────────
print("\n[4] Model precision at different confidence thresholds:")
print(f"   {'Threshold':>10} {'Signals':>8} {'Precision':>10} {'Lift':>8}")
print(f"   {'-'*40}")
base_rate = y_test.mean()

for thr in [0.50, 0.55, 0.60, 0.65, 0.70]:
    preds = (xg_proba >= thr).astype(int)
    if preds.sum() == 0: continue
    prec  = y_test[preds==1].mean()
    lift  = prec / base_rate
    print(f"   {thr:>10.0%} {preds.sum():>8,} {prec*100:>9.1f}% {lift:>7.2f}x")

# ── Save model + metadata ─────────────────────────────────────────────────
import pickle

with open('xgb_model.pkl','wb') as f:
    pickle.dump(xg, f)
with open('scaler.pkl','wb') as f:
    pickle.dump(scaler, f)

pd.DataFrame({'feature': FEATURE_COLS}).to_csv('feature_list.csv', index=False)

# Save test predictions for backtesting
test_out = test[['Date','ticker','target']].copy()
test_out['xg_proba']    = xg_proba
test_out['signal']      = xg_pred_thr
test_out['pred_return'] = pred_return
test_out['close']       = test['Close'] if 'Close' in test.columns else np.nan
test_out.to_csv('test_predictions.csv', index=False)

print(f"""
{'='*65}
 STEP 3 COMPLETE
{'='*65}
 XGBoost AUC     : {xg_auc:.3f}  (vs 0.500 = random)
 High-conf prec  : {xg_prec*100:.1f}% (vs {base_rate*100:.1f}% base rate)
 Lift at 60%     : {xg_prec/base_rate:.2f}x better than random

 Saved:
   xgb_model.pkl           ← trained model
   scaler.pkl              ← feature scaler
   test_predictions.csv    ← predictions on test set

 Next: Run step4_backtest.py
{'='*65}
""")
