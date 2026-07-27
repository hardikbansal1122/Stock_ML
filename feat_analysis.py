import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import joblib

features_new = pd.read_csv('features.csv')
features_new['Date'] = pd.to_datetime(features_new['Date'])

EXCLUDED_FEATURES = {'Date','ticker','target','future_ret_5d','ret_5d_net','Open','High','Low','Close','Volume'}
TEMPORARILY_EXCLUDED_FEATURES = {'ret_60d','ma5','ma10','ma20','ma50','momentum_acceleration','rsi14','vol_ma20','nifty_ret_1d','nifty_ret_10d','nifty_ret_60d','nifty_rsi14','nifty_volatility_20d','nifty_price_vs_ma200','nifty_ma50_vs_ma200'}
FEATURE_COLS = [col for col in features_new.columns if col not in EXCLUDED_FEATURES | TEMPORARILY_EXCLUDED_FEATURES]

model_new = joblib.load('xgb_model.pkl')
X_sample_new = features_new[(features_new['Date'] >= '2024-07-01')][FEATURE_COLS].sample(5000, random_state=42)
explainer_new = shap.TreeExplainer(model_new)
shap_values_new = explainer_new.shap_values(X_sample_new)

# 1. SHAP rankings
shap_df = pd.DataFrame(np.abs(shap_values_new), columns=FEATURE_COLS).mean().sort_values(ascending=False)
gain_imp = pd.Series(model_new.get_booster().get_score(importance_type='gain'))
split_imp = pd.Series(model_new.get_booster().get_score(importance_type='weight'))

print("=== 1. FULL SHAP RANKING ===")
for col in shap_df.index:
    print(f"{col}: SHAP={shap_df[col]:.5f}, Gain={gain_imp.get(col, 0):.2f}, Split={split_imp.get(col, 0)}")

print("\n=== 2. ZERO SHAP ===")
for col in shap_df.index:
    if shap_df[col] < 0.005:
        print(f"Low importance: {col}")

# 3. Correlations
print("\n=== 3. CORRELATIONS > 0.90 ===")
corr = X_sample_new.corr()
for i in range(len(corr.columns)):
    for j in range(i+1, len(corr.columns)):
        if abs(corr.iloc[i,j]) > 0.90:
            print(f"High corr: {corr.columns[i]} and {corr.columns[j]} = {corr.iloc[i,j]:.3f}")

