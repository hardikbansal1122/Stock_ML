#!/usr/bin/env python3
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
import xgboost as xgb
from sklearn.metrics import roc_auc_score, average_precision_score
from scipy.stats import spearmanr

from walkforward_validation import (
    load_price_series, build_trade_df, simulate_portfolio,
    TRAIN_MONTHS, TEST_MONTHS, GAP_DAYS, STEP_MONTHS, CONFIDENCE_THRESHOLD, HOLD_DAYS
)

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
FEATURE_FILE = ROOT / 'features.csv'

# Base 16 features (3 are missing due to early dataset removal, leaving 13)
BASELINE_FEATURES = [
    'price_vs_ma50', 'nifty_above_ma50', 'ma10_vs_ma50', 'ret_5d', 'ret_10d', 'ret_20d',
    'rs_ret_20d', 'rs_ret_60d', 'rs_acceleration', 'volatility_5d', 'volatility_20d',
    'hl_range', 'bb_position', 'updown_vol_ratio_10', 'nifty_ret_5d', 'nifty_ret_20d'
]

EXPERIMENTS = {
    'Baseline': BASELINE_FEATURES,
    'Combined Optimal Set': BASELINE_FEATURES + [
        'cs_rank_20d', 'ret_5d_pctile', 'ret_60d_pctile', '52_week_range_position'
    ]
}

def compute_ndcg_v2(y_true, total_ones, k):
    y_true = np.asarray(y_true)[:k]
    dcg = np.sum(y_true / np.log2(np.arange(2, len(y_true) + 2)))
    ideal_ones = min(total_ones, k)
    if ideal_ones == 0: return 0.0
    ideal_y = np.ones(ideal_ones)
    idcg = np.sum(ideal_y / np.log2(np.arange(2, len(ideal_y) + 2)))
    return dcg / idcg

def build_folds(dates):
    max_date = dates.iloc[-1]
    folds = []
    train_start = dates.iloc[0]
    while True:
        train_end_target = train_start + pd.DateOffset(months=TRAIN_MONTHS) - pd.Timedelta(days=1)
        train_end_idx = dates.searchsorted(train_end_target, side='right') - 1
        if train_end_idx < 0: break
        train_end = dates[train_end_idx]
        test_start_idx = train_end_idx + GAP_DAYS + 1
        if test_start_idx >= len(dates): break
        test_start = dates[test_start_idx]
        test_end_target = test_start + pd.DateOffset(months=TEST_MONTHS) - pd.Timedelta(days=1)
        if test_end_target > max_date: break
        test_end = dates[dates.searchsorted(test_end_target, side='right') - 1]
        if test_end < test_start: break
        folds.append((train_start, train_end, test_start, test_end))
        train_start = train_start + pd.DateOffset(months=STEP_MONTHS)
        if train_start > max_date: break
    return folds

def main():
    print("Loading data...")
    df = pd.read_csv(FEATURE_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    prices = load_price_series()
    
    dates = pd.Series(df['Date'].unique()).sort_values().reset_index(drop=True)
    folds = build_folds(dates)
    
    # Filter to existing columns only
    for exp_name, features in EXPERIMENTS.items():
        EXPERIMENTS[exp_name] = [f for f in features if f in df.columns]
    
    results = []
    
    for exp_name, features in EXPERIMENTS.items():
        print(f"\nRunning {exp_name} with {len(features)} features...")
        
        all_preds = []
        for train_start, train_end, test_start, test_end in folds:
            train = df[(df['Date'] >= train_start) & (df['Date'] <= train_end)].dropna(subset=features)
            test = df[(df['Date'] >= test_start) & (df['Date'] <= test_end)].dropna(subset=features)
            if len(train) == 0 or len(test) == 0: continue
            
            X_train, y_train = train[features], train['target']
            X_test, y_test = test[features], test['target']
            
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dtest = xgb.DMatrix(X_test, label=y_test)
            
            params = {
                'objective': 'binary:logistic',
                'eval_metric': 'auc',
                'max_depth': 4,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'seed': 42
            }
            
            model = xgb.train(params, dtrain, num_boost_round=100, evals=[(dtest, 'test')], early_stopping_rounds=10, verbose_eval=False)
            preds = model.predict(dtest, iteration_range=(0, model.best_iteration + 1))
            
            test_res = test[['Date', 'ticker', 'target', 'ret_5d_net']].copy()
            test_res['xg_proba'] = preds
            test_res['pred_return'] = preds
            all_preds.append(test_res)
            
        if not all_preds:
            continue
            
        full_preds = pd.concat(all_preds)
        full_preds = full_preds.sort_values(['Date', 'ticker'])
        
        roc = roc_auc_score(full_preds['target'], full_preds['xg_proba'])
        pr = average_precision_score(full_preds['target'], full_preds['xg_proba'])
        
        daily_metrics = []
        for date, group in full_preds.groupby('Date'):
            group = group.sort_values('xg_proba', ascending=False)
            y_true = group['target'].values
            n = len(y_true)
            if n < 20: continue
            
            p5 = np.mean(y_true[:5])
            p10 = np.mean(y_true[:10])
            p20 = np.mean(y_true[:20])
            ndcg = compute_ndcg_v2(y_true, np.sum(y_true), n)
            
            base = np.mean(y_true)
            decile = max(1, int(0.1*n))
            lift = np.mean(y_true[:decile]) / base if base > 0 else 1.0
            
            ic, _ = spearmanr(group['xg_proba'], group['ret_5d_net'])
            if np.isnan(ic): ic = 0
            
            daily_metrics.append({'P@5': p5, 'P@10': p10, 'P@20': p20, 'NDCG': ndcg, 'Lift': lift, 'IC': ic})
            
        dm = pd.DataFrame(daily_metrics)
        mean_p5 = dm['P@5'].mean()
        mean_p10 = dm['P@10'].mean()
        mean_p20 = dm['P@20'].mean()
        mean_ndcg = dm['NDCG'].mean()
        mean_lift = dm['Lift'].mean()
        mean_ic = dm['IC'].mean()
        icir = mean_ic / dm['IC'].std() if dm['IC'].std() > 0 else 0
        
        # Portfolio Simulator
        trades_df = build_trade_df(full_preds[full_preds['xg_proba'] >= CONFIDENCE_THRESHOLD], prices)
        
        if len(trades_df) > 0:
            port, cagr, sharpe = simulate_portfolio(trades_df, prices, rank_by_pred_return=False)
            win_rate = trades_df['Won'].mean()
            max_dd = port['Drawdown'].min()
        else:
            cagr = 0.0
            sharpe = 0.0
            win_rate = 0.0
            max_dd = 0.0
        
        res = {
            'Experiment': exp_name,
            'ROC-AUC': f"{roc:.4f}",
            'PR-AUC': f"{pr:.4f}",
            'P@5': f"{mean_p5:.1%}",
            'P@10': f"{mean_p10:.1%}",
            'P@20': f"{mean_p20:.1%}",
            'NDCG': f"{mean_ndcg:.4f}",
            'Lift': f"{mean_lift:.2f}x",
            'IC': f"{mean_ic:.4f}",
            'ICIR': f"{icir:.4f}",
            'Win Rate': f"{win_rate:.1%}",
            'CAGR': f"{cagr:.1%}",
            'Sharpe': f"{sharpe:.2f}",
            'Max Drawdown': f"{max_dd:.1%}",
            'Trades': len(trades_df)
        }
        results.append(res)
        print(f"  AUC: {roc:.4f}, CAGR: {cagr:.1%}, Win Rate: {win_rate:.1%}, Trades: {len(trades_df)}")

    df_res = pd.DataFrame(results)
    
    def df_to_markdown(df):
        cols = df.columns.tolist()
        res = "|" + "|".join(cols) + "|\n"
        res += "|" + "|".join(["---"] * len(cols)) + "|\n"
        for _, row in df.iterrows():
            res += "|" + "|".join(str(row[c]) for c in cols) + "|\n"
        return res
        
    print("\nFinal Results:")
    print(df_to_markdown(df_res))

if __name__ == '__main__':
    main()
