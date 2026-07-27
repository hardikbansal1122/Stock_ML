import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.calibration import calibration_curve
import os

print("Loading data...")
features_new = pd.read_csv('features.csv')
features_new['Date'] = pd.to_datetime(features_new['Date'])

# 1. Recreate OLD dataset
# Read raw prices to compute old target
print("Recreating old dataset...")
raw_dfs = []
for ticker in features_new['ticker'].unique():
    f = f"data/{ticker}.csv"
    if os.path.exists(f):
        df = pd.read_csv(f)
        df['ticker'] = ticker
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        close_col = 'Close' if 'Close' in df.columns else 'Adj Close'
        df['old_future_ret_5d'] = df[close_col].shift(-5) / df[close_col] - 1
        raw_dfs.append(df[['Date', 'ticker', 'old_future_ret_5d']])

raw_df = pd.concat(raw_dfs, ignore_index=True)
features_old = pd.merge(features_new.drop(columns=['future_ret_5d', 'target']), raw_df, on=['ticker', 'Date'], how='inner')
features_old['target'] = (features_old['old_future_ret_5d'] > 0.02).astype(int)

# 2. Train OLD model
print("Training old model...")
EXCLUDED_FEATURES = {'Date','ticker','target','future_ret_5d','old_future_ret_5d','ret_5d_net','Open','High','Low','Close','Volume'}
TEMPORARILY_EXCLUDED_FEATURES = {'ret_60d','ma5','ma10','ma20','ma50','momentum_acceleration','rsi14','vol_ma20','nifty_ret_1d','nifty_ret_10d','nifty_ret_60d','nifty_rsi14','nifty_volatility_20d','nifty_price_vs_ma200','nifty_ma50_vs_ma200'}
FEATURE_COLS = [col for col in features_new.columns if col not in EXCLUDED_FEATURES | TEMPORARILY_EXCLUDED_FEATURES]

train_mask_old = (features_old['Date'] < '2024-07-01')
test_mask_old = (features_old['Date'] >= '2024-07-01')

X_train_old = features_old[train_mask_old][FEATURE_COLS]
y_train_old = features_old[train_mask_old]['target']
X_test_old = features_old[test_mask_old][FEATURE_COLS]
y_test_old = features_old[test_mask_old]['target']

xgb_params = {
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'learning_rate': 0.05,
    'max_depth': 4,
    'min_child_weight': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
    'n_jobs': -1
}
model_old = xgb.XGBClassifier(**xgb_params, n_estimators=300)
model_old.fit(X_train_old, y_train_old)
preds_old = model_old.predict_proba(X_test_old)[:, 1]

# 3. Load NEW model predictions
print("Loading new model...")
preds_new_df = pd.read_csv('test_predictions.csv')
preds_new = preds_new_df['xg_proba'].values
import joblib
model_new = joblib.load('xgb_model.pkl')

print("\n" + "="*50)
print(" 1. PROBABILITY DISTRIBUTION")
print("="*50)
print(f"{'Metric':<15} | {'OLD (Leaked)':<15} | {'NEW (Clean)':<15}")
print("-" * 50)
print(f"{'Mean':<15} | {np.mean(preds_old):<15.4f} | {np.mean(preds_new):<15.4f}")
print(f"{'Median':<15} | {np.median(preds_old):<15.4f} | {np.median(preds_new):<15.4f}")
print(f"{'Std Dev':<15} | {np.std(preds_old):<15.4f} | {np.std(preds_new):<15.4f}")
print(f"{'90th Pctile':<15} | {np.percentile(preds_old, 90):<15.4f} | {np.percentile(preds_new, 90):<15.4f}")
print(f"{'95th Pctile':<15} | {np.percentile(preds_old, 95):<15.4f} | {np.percentile(preds_new, 95):<15.4f}")
print(f"{'99th Pctile':<15} | {np.percentile(preds_old, 99):<15.4f} | {np.percentile(preds_new, 99):<15.4f}")

print("\n" + "="*50)
print(" 2. PREDICTIONS ABOVE THRESHOLD")
print("="*50)
threshs = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
print(f"{'Threshold':<10} | {'OLD (Leaked)':<15} | {'NEW (Clean)':<15}")
print("-" * 50)
for t in threshs:
    old_c = np.sum(preds_old >= t)
    new_c = np.sum(preds_new >= t)
    print(f"{t:<10.2f} | {old_c:<15} | {new_c:<15}")

print("\n" + "="*50)
print(" 3. FEATURE IMPORTANCE (Top 10)")
print("="*50)
old_imp = pd.Series(model_old.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False).head(10)
new_imp = pd.Series(model_new.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False).head(10)
print("OLD MODEL TOP 10:")
print(old_imp)
print("\nNEW MODEL TOP 10:")
print(new_imp)

print("\n" + "="*50)
print(" 4. CALIBRATION / RELIABILITY")
print("="*50)
prob_true_old, prob_pred_old = calibration_curve(y_test_old, preds_old, n_bins=10)
print("OLD MODEL Calibration (Predicted vs Actual):")
for p, t in zip(prob_pred_old, prob_true_old):
    print(f"  Pred: {p:.3f} -> True: {t:.3f}")

y_test_new = features_new[(features_new['Date'] >= '2024-07-01')]['target']
prob_true_new, prob_pred_new = calibration_curve(y_test_new, preds_new, n_bins=10)
print("\nNEW MODEL Calibration (Predicted vs Actual):")
for p, t in zip(prob_pred_new, prob_true_new):
    print(f"  Pred: {p:.3f} -> True: {t:.3f}")

print("\n" + "="*50)
print(" 5. SHAP ANALYSIS (Avg |SHAP| value)")
print("="*50)
# Subsample for speed
X_sample_old = X_test_old.sample(5000, random_state=42)
explainer_old = shap.TreeExplainer(model_old)
shap_values_old = explainer_old.shap_values(X_sample_old)

# New model
X_sample_new = features_new[(features_new['Date'] >= '2024-07-01')][FEATURE_COLS].sample(5000, random_state=42)
explainer_new = shap.TreeExplainer(model_new)
shap_values_new = explainer_new.shap_values(X_sample_new)

shap_old_df = pd.DataFrame(np.abs(shap_values_old), columns=FEATURE_COLS).mean().sort_values(ascending=False).head(5)
shap_new_df = pd.DataFrame(np.abs(shap_values_new), columns=FEATURE_COLS).mean().sort_values(ascending=False).head(5)

print("OLD MODEL SHAP TOP 5:")
print(shap_old_df)
print("\nNEW MODEL SHAP TOP 5:")
print(shap_new_df)

print("\nDone.")
