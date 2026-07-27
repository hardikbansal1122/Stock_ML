import pandas as pd
import numpy as np

# Load predictions
preds = pd.read_csv('test_predictions.csv')
# Ensure proper datetime
preds['Date'] = pd.to_datetime(preds['Date'])

# Overall top 10 predictions by probability
top10 = preds.nlargest(10, 'xg_proba')
print('=== Overall Top 10 Predictions (by probability) ===')
print(top10[['Date', 'ticker', 'xg_proba', 'target', 'pred_return']])
overall_precision = top10['target'].sum() / 10
print(f'Overall Precision@10: {overall_precision:.3f}')

# Daily Precision@10 as used in evaluation (average across days)
# For each day, take top 10 predictions (or fewer if less than 10)

daily_precisions = []
for date, group in preds.groupby('Date'):
    top = group.nlargest(min(10, len(group)), 'xg_proba')
    if len(top) == 0:
        continue
    daily_prec = top['target'].sum() / len(top)
    daily_precisions.append(daily_prec)
if daily_precisions:
    average_daily_p10 = np.mean(daily_precisions)
else:
    average_daily_p10 = float('nan')
print(f'Average Daily Precision@10: {average_daily_p10:.3f}')
print(f'Number of trading days evaluated: {len(daily_precisions)}')

# Calibration deciles
bins = pd.qcut(preds['xg_proba'], q=10, duplicates='drop')
calibration = preds.groupby(bins)['target'].mean()
print('\nCalibration (average target rate per probability decile):')
print(calibration)

# High confidence predictions >0.75
high_conf = preds[preds['xg_proba'] > 0.75]
print(f"\nNumber of predictions with prob > 0.75: {len(high_conf)}")
if len(high_conf) > 0:
    print(f"Fraction of high-confidence that are true positives: {high_conf['target'].mean():.3f}")
else:
    print('No high-confidence predictions')
