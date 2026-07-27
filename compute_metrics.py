import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
import json

def compute_metrics():
    # 1. AUC and PR-AUC
    preds = pd.read_csv('test_predictions.csv')
    y_true = preds['target']
    y_prob = preds['xg_proba']
    auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    
    # Precision@K
    preds_sorted = preds.sort_values('xg_proba', ascending=False)
    p10 = preds_sorted.head(10)['target'].mean()
    p20 = preds_sorted.head(20)['target'].mean()
    
    # 2. Portfolio metrics
    trades = pd.read_csv('backtest_trades.csv')
    # Filter trades to threshold 0.75 just in case, or just take the overall win rate?
    # Backtest saves trades for the baseline threshold. Let's just use what's there.
    win_rate = trades['Won'].mean() if len(trades) > 0 else 0
    
    port = pd.read_csv('portfolio_history.csv')
    port['Date'] = pd.to_datetime(port['Date'])
    
    # CAGR
    start_val = 100000
    end_val = port['TotalValue'].iloc[-1]
    days = (port['Date'].max() - port['Date'].min()).days
    years = days / 365.25
    cagr = (end_val / start_val) ** (1 / years) - 1 if years > 0 else 0
    
    # Sharpe (assuming daily risk-free rate of 0 for simplicity)
    port['DailyRet'] = port['TotalValue'].pct_change()
    mean_ret = port['DailyRet'].mean()
    std_ret = port['DailyRet'].std()
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
    
    # Feature count
    import joblib
    model = joblib.load('xgb_model.pkl')
    feat_count = len(model.feature_names_in_)
    
    metrics = {
        'AUC': float(auc),
        'PR-AUC': float(pr_auc),
        'Win Rate': float(win_rate),
        'Precision@10': float(p10),
        'Precision@20': float(p20),
        'Sharpe': float(sharpe),
        'CAGR': float(cagr),
        'Feature Count': int(feat_count)
    }
    return metrics

if __name__ == '__main__':
    m = compute_metrics()
    with open('baseline_metrics.json', 'w') as f:
        json.dump(m, f)
    print("Baseline metrics saved to baseline_metrics.json")
