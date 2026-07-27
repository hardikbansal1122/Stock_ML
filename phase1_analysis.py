import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
import json
import shap
import joblib

def analyze_phase1():
    # 1. Metrics
    preds = pd.read_csv('test_predictions.csv')
    y_true = preds['target']
    y_prob = preds['xg_proba']
    auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    brier = brier_score_loss(y_true, y_prob)
    
    preds_sorted = preds.sort_values('xg_proba', ascending=False)
    p10 = preds_sorted.head(10)['target'].mean()
    p20 = preds_sorted.head(20)['target'].mean()
    avg_conf = y_prob.mean()
    
    trades = pd.read_csv('backtest_trades.csv')
    total_trades = len(trades)
    win_rate = trades['Won'].mean() if len(trades) > 0 else 0
    avg_ret = trades['NetReturn'].mean() if len(trades) > 0 else 0
    med_ret = trades['NetReturn'].median() if len(trades) > 0 else 0
    
    port = pd.read_csv('portfolio_history.csv')
    port['Date'] = pd.to_datetime(port['Date'])
    
    start_val = 100000
    end_val = port['TotalValue'].iloc[-1]
    days = (port['Date'].max() - port['Date'].min()).days
    years = days / 365.25
    cagr = (end_val / start_val) ** (1 / years) - 1 if years > 0 else 0
    
    port['DailyRet'] = port['TotalValue'].pct_change()
    mean_ret = port['DailyRet'].mean()
    std_ret = port['DailyRet'].std()
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret > 0 else 0
    
    port['CumMax'] = port['TotalValue'].cummax()
    port['Drawdown'] = port['TotalValue'] / port['CumMax'] - 1
    max_dd = port['Drawdown'].min()
    
    model = joblib.load('xgb_model.pkl')
    feat_count = len(model.feature_names_in_)
    
    metrics = {
        'AUC': auc,
        'PR-AUC': pr_auc,
        'Brier Score': brier,
        'Win Rate': win_rate,
        'Average Return': avg_ret,
        'Median Return': med_ret,
        'CAGR': cagr,
        'Sharpe Ratio': sharpe,
        'Maximum Drawdown': max_dd,
        'Precision@10': p10,
        'Precision@20': p20,
        'Total Trades': total_trades,
        'Average Confidence': avg_conf,
        'Feature Count': feat_count
    }
    
    # 2. SHAP
    features_new = pd.read_csv('features.csv')
    features_new['Date'] = pd.to_datetime(features_new['Date'])
    X_sample_new = features_new[(features_new['Date'] >= '2024-07-01')][model.feature_names_in_].sample(5000, random_state=42)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample_new)
    shap_df = pd.DataFrame(np.abs(shap_values), columns=model.feature_names_in_).mean().sort_values(ascending=False)
    
    # 3. Walkforward
    wf = pd.read_csv('walkforward_results.csv')
    
    with open('phase1_analysis.json', 'w') as f:
        json.dump({
            'metrics': metrics,
            'shap': shap_df.to_dict(),
            'walkforward': wf.to_dict(orient='records')
        }, f, indent=2)
    print("Analysis saved to phase1_analysis.json")

if __name__ == '__main__':
    analyze_phase1()
