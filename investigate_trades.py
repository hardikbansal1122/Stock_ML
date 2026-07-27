import pandas as pd

# 1. Check if the simulator rejected any trades in the new baseline
sweep = pd.read_csv('threshold_sweep_summary.csv')
t75 = sweep[sweep['Threshold'] == 0.75].iloc[0]
print(f"=== PORTFOLIO SIMULATOR ===")
print(f"New Baseline (75% Threshold):")
print(f"  Signals Generated: {t75['Signals']}")
print(f"  Trades Simulated: {t75['Trades']}")
print(f"  Rejected Trades: {t75['Signals'] - t75['Trades']}")

# 2. Check the capacity of the portfolio in the new baseline
history = pd.read_csv('portfolio_history.csv')
max_positions = history['PositionsOpen'].max()
avg_positions = history['PositionsOpen'].mean()
days_at_max = (history['PositionsOpen'] == 10).sum()
print(f"\nPortfolio Capacity Utilization (New Baseline):")
print(f"  Max Concurrent Positions: {max_positions}")
print(f"  Avg Concurrent Positions: {avg_positions:.1f}")
print(f"  Days at Max Capacity (10): {days_at_max} out of {len(history)} days")

# 3. Analyze the probability distribution of the new model
preds = pd.read_csv('test_predictions.csv')
conf_75 = (preds['xg_proba'] >= 0.75).sum()
print(f"\n=== SIGNAL GENERATION ===")
print(f"Total test samples: {len(preds)}")
print(f"Predictions >= 0.75: {conf_75}")

# Group by probability bins to see distribution
bins = [0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0]
dist = pd.cut(preds['xg_proba'], bins=bins).value_counts().sort_index()
print(f"\nProbability Distribution:")
print(dist)
