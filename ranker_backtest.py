#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, average_precision_score
from scipy.stats import spearmanr
import warnings

from walkforward_validation import load_price_series, simulate_portfolio, HOLD_DAYS

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
PREDS_FILE = ROOT / 'ranker_preds.csv'
REPORT_MD = ROOT / 'RANKER_REPORT.md'
STARTING_CAPITAL = 100_000
MAX_POSITIONS = 10

def compute_ndcg_v2(y_true, total_ones, k):
    y_true = np.asarray(y_true)[:k]
    dcg = np.sum(y_true / np.log2(np.arange(2, len(y_true) + 2)))
    ideal_ones = min(total_ones, k)
    if ideal_ones == 0: return 0.0
    ideal_y = np.ones(ideal_ones)
    idcg = np.sum(ideal_y / np.log2(np.arange(2, len(ideal_y) + 2)))
    return dcg / idcg

def compute_mrr(y_true):
    for i, val in enumerate(y_true):
        if val == 1:
            return 1.0 / (i + 1)
    return 0.0

def build_trade_df_top_n(signals_df, prices, score_col, top_n=10):
    trades = []
    for date, group in signals_df.groupby('Date'):
        group = group.sort_values(score_col, ascending=False).head(top_n)
        for _, row in group.iterrows():
            ticker = row['ticker']
            if ticker in prices:
                trades.append({
                    'Date': date,
                    'ticker': ticker,
                    'pred_return': row[score_col]
                })
    return pd.DataFrame(trades)

def simulate_portfolio_safe(trades_df, prices):
    if len(trades_df) == 0:
        return {'Drawdown': pd.Series([0])}, 0.0, 0.0, 0.0, 0.0, 0
        
    try:
        port, cagr, sharpe = simulate_portfolio(trades_df, prices, rank_by_pred_return=True)
        win_rate = trades_df['Won'].mean()
        avg_ret = trades_df['NetReturn'].mean()
        max_dd = port['Drawdown'].min()
        return port, cagr, sharpe, max_dd, win_rate, avg_ret, len(trades_df)
    except Exception as e:
        print("Simulation error:", e)
        return {'Drawdown': pd.Series([0])}, 0.0, 0.0, 0.0, 0.0, 0, 0

def evaluate_model(df, score_col, prices):
    roc = roc_auc_score(df['target'], df[score_col])
    pr = average_precision_score(df['target'], df[score_col])
    
    daily_metrics = []
    for date, group in df.groupby('Date'):
        group = group.sort_values(score_col, ascending=False)
        y_true = group['target'].values
        n = len(y_true)
        if n < 20: continue
        
        p5 = np.mean(y_true[:5])
        p10 = np.mean(y_true[:10])
        p20 = np.mean(y_true[:20])
        
        total_ones = np.sum(y_true)
        ndcg5 = compute_ndcg_v2(y_true, total_ones, 5)
        ndcg10 = compute_ndcg_v2(y_true, total_ones, 10)
        
        mrr = compute_mrr(y_true)
        
        base = np.mean(y_true)
        decile = max(1, int(0.1*n))
        lift = np.mean(y_true[:decile]) / base if base > 0 else 1.0
        
        daily_metrics.append({
            'P@5': p5, 'P@10': p10, 'P@20': p20, 
            'NDCG@5': ndcg5, 'NDCG@10': ndcg10, 
            'MRR': mrr, 'Lift': lift
        })
        
    dm = pd.DataFrame(daily_metrics)
    stats = dm.mean().to_dict()
    
    trades_df = build_trade_df_top_n(df, prices, score_col, top_n=10)
    port, cagr, sharpe, max_dd, win_rate, avg_ret, num_trades = simulate_portfolio_safe(trades_df, prices)
    
    return {
        'ROC-AUC': roc,
        'PR-AUC': pr,
        'P@5': stats['P@5'],
        'P@10': stats['P@10'],
        'P@20': stats['P@20'],
        'NDCG@5': stats['NDCG@5'],
        'NDCG@10': stats['NDCG@10'],
        'MRR': stats['MRR'],
        'Lift': stats['Lift'],
        'CAGR': cagr,
        'Sharpe': sharpe,
        'Max Drawdown': max_dd,
        'Win Rate': win_rate,
        'Avg Trade Ret': avg_ret,
        'Trades': num_trades
    }

def main():
    print("Loading predictions and prices...")
    df = pd.read_csv(PREDS_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    prices = load_price_series()
    
    print("Evaluating Classifier...")
    clf_res = evaluate_model(df, 'classifier_score', prices)
    
    print("Evaluating Ranker...")
    rnk_res = evaluate_model(df, 'ranker_score', prices)
    
    metrics_order = [
        'NDCG@5', 'NDCG@10', 'P@5', 'P@10', 'P@20', 'MRR', 'Lift',
        'CAGR', 'Sharpe', 'Max Drawdown', 'Win Rate', 'Avg Trade Ret', 'Trades',
        'ROC-AUC', 'PR-AUC'
    ]
    
    res_df = pd.DataFrame([clf_res, rnk_res], index=['XGBClassifier', 'XGBRanker'])[metrics_order]
    
    # Format
    format_dict = {
        'NDCG@5': '{:.4f}', 'NDCG@10': '{:.4f}',
        'P@5': '{:.1%}', 'P@10': '{:.1%}', 'P@20': '{:.1%}',
        'MRR': '{:.4f}', 'Lift': '{:.2f}x',
        'CAGR': '{:.1%}', 'Sharpe': '{:.2f}', 'Max Drawdown': '{:.1%}',
        'Win Rate': '{:.1%}', 'Avg Trade Ret': '{:.2%}', 'Trades': '{:d}',
        'ROC-AUC': '{:.4f}', 'PR-AUC': '{:.4f}'
    }
    
    for col, fmt in format_dict.items():
        res_df[col] = res_df[col].apply(lambda x: fmt.format(x))
        
    print("\nFinal Comparison:")
    print(res_df.to_string())
    
    md = "# Learning-to-Rank Evaluation (Phase 2)\n\n"
    md += "## Performance Comparison\n\n"
    
    cols = res_df.reset_index().columns.tolist()
    md += "|" + "|".join(cols) + "|\n"
    md += "|" + "|".join(["---"] * len(cols)) + "|\n"
    for idx, row in res_df.iterrows():
        md += "|" + str(idx) + "|" + "|".join(str(row[c]) for c in res_df.columns) + "|\n"
        
    md += """
## Architecture Differences
- **Classifier**: `binary:logistic`. Optimizes for global probability (log-loss) across the entire dataset.
- **Ranker**: `rank:ndcg`. Optimizes for relative ordering (pairwise/listwise) per day using query groups.

## Training Procedure
Both models were trained using exactly the same 14 features on a 24-month rolling window with a 3-month test period. The ranker required grouping samples by `Date` via a `qid` column.

## Recommendation
*(See data above to evaluate)*

"""
    with open(REPORT_MD, 'w') as f:
        f.write(md)
        
    print(f"\nReport saved to {REPORT_MD.name}")

if __name__ == "__main__":
    main()
