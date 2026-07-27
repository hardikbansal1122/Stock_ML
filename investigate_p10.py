import pandas as pd
import numpy as np

# 1. Load predictions
preds = pd.read_csv('test_predictions.csv')
preds['Date'] = pd.to_datetime(preds['Date'])

# 2. Load features to get future_ret_5d
features = pd.read_csv('features.csv')
features['Date'] = pd.to_datetime(features['Date'])

# Merge
merged = pd.merge(preds, features[['Date', 'ticker', 'future_ret_5d']], on=['Date', 'ticker'], how='left')

# 3. Sort by confidence
merged_sorted = merged.sort_values('xg_proba', ascending=False)

# 4. Extract Top 10 and Top 20
top10 = merged_sorted.head(10)
top20 = merged_sorted.head(20)

print("=== TOP 10 PREDICTIONS ===")
print(top10[['Date', 'ticker', 'xg_proba', 'target', 'future_ret_5d']].to_string(index=False))

print("\n=== METRICS ===")
print(f"Precision@10: {top10['target'].mean() * 100:.2f}%")
print(f"Precision@20: {top20['target'].mean() * 100:.2f}%")

print("\n=== DISTRIBUTION CHECK ===")
# Check how many test predictions we actually have
print(f"Total test predictions: {len(preds)}")
print(f"Number of predictions >= 0.75: {(preds['xg_proba'] >= 0.75).sum()}")
print(f"Max xg_proba: {preds['xg_proba'].max():.4f}")

# Group by date to see if top 10 are concentrated on a single anomalous day
top10_dates = top10['Date'].value_counts()
print("\n=== TOP 10 DATES ===")
print(top10_dates)

# Let's also load the backtest_trades.csv to see what the simulator did
trades = pd.read_csv('backtest_trades.csv')
print("\n=== TOP 10 HIGHEST CONFIDENCE TRADES EXECUTED ===")
top_trades = trades.sort_values('Confidence', ascending=False).head(10)
print(top_trades[['Date', 'Ticker', 'Confidence', 'Return', 'Won']].to_string(index=False))

