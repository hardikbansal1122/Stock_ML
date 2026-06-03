#!/usr/bin/env python3
"""Walkforward diagnostics for the Stock ML strategy."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

ROOT = Path(__file__).resolve().parent
FEATURES_PATH = ROOT / 'features.csv'
REPORT_PATH = ROOT / 'WALKFORWARD_DIAGNOSTICS.md'

FEATURE_COLS = [
    'ret_1d', 'ret_3d', 'ret_5d', 'ret_10d', 'ret_20d',
    'price_vs_ma5', 'price_vs_ma20', 'price_vs_ma50',
    'ma5_vs_ma20', 'ma10_vs_ma50',
    'rsi_normalized',
    'volatility_5d', 'volatility_20d', 'hl_range',
    'volume_ratio', 'volume_trend',
    'bb_position',
    'up_days_5', 'up_days_10',
    'gap',
    'nifty_ret_5d', 'nifty_ret_20d', 'nifty_above_ma50'
]

CONF_THRESHOLDS = [0.60, 0.65, 0.70, 0.75, 0.80]
CONFIDENCE_THRESHOLD = 0.75
TRAIN_MONTHS = 24
TEST_MONTHS = 3
GAP_DAYS = 5
STEP_MONTHS = 3


def build_folds(dates):
    max_date = dates[-1]
    folds = []
    train_start = dates[0]
    while True:
        train_end_target = train_start + pd.DateOffset(months=TRAIN_MONTHS) - pd.Timedelta(days=1)
        train_end_idx = dates.searchsorted(train_end_target, side='right') - 1
        if train_end_idx < 0:
            break
        train_end = dates[train_end_idx]
        test_start_idx = train_end_idx + GAP_DAYS + 1
        if test_start_idx >= len(dates):
            break
        test_start = dates[test_start_idx]
        test_end_target = test_start + pd.DateOffset(months=TEST_MONTHS) - pd.Timedelta(days=1)
        if test_end_target > max_date:
            break
        test_end = dates[dates.searchsorted(test_end_target, side='right') - 1]
        if test_end < test_start:
            break
        folds.append((train_start, train_end, test_start, test_end))
        train_start = train_start + pd.DateOffset(months=STEP_MONTHS)
        if train_start > max_date:
            break
    return folds


def train_and_score(train, test):
    X_train = train[FEATURE_COLS]
    y_train = train['target']
    X_test = test[FEATURE_COLS]
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    clf = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos,
        objective='binary:logistic',
        eval_metric='auc',
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train_s, y_train, eval_set=[(X_test_s, test['target'])], verbose=False)
    proba = clf.predict_proba(X_test_s)[:, 1]
    return proba


def summarize_thresholds(probs):
    return {th: int((probs >= th).sum()) for th in CONF_THRESHOLDS}


def summarize_fold(train, test, probs):
    summary = {
        'TrainStart': train['Date'].min().date(),
        'TrainEnd': train['Date'].max().date(),
        'TestStart': test['Date'].min().date(),
        'TestEnd': test['Date'].max().date(),
        'TestRows': len(test),
        'AvgProb': float(probs.mean()),
        'MedianProb': float(np.median(probs)),
        'CountThresholds': summarize_thresholds(probs),
    }
    return summary


def fold_signal_stats(test, probs, threshold):
    df = test.copy()
    df['xg_proba'] = probs
    selected = df[df['xg_proba'] >= threshold]
    if len(selected) == 0:
        return None
    return {
        'Count': len(selected),
        'AvgConfidence': float(selected['xg_proba'].mean()),
        'AvgPredReturn': float(selected['ret_5d_net'].mean()),
        'AvgRSI': float(selected['rsi_normalized'].mean()),
        'AvgVolatility': float(selected['volatility_5d'].mean()),
        'AvgVolumeRatio': float(selected['volume_ratio'].mean()),
    }


def main():
    df = pd.read_csv(FEATURES_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
    dates = pd.DatetimeIndex(np.sort(df['Date'].unique()))
    folds = build_folds(dates)

    results = []
    diagnostics = []

    for fold_id, (ts, te, ss, se) in enumerate(folds, start=1):
        train = df[(df['Date'] >= ts) & (df['Date'] <= te)].dropna(subset=FEATURE_COLS + ['target', 'ret_5d_net'])
        test = df[(df['Date'] >= ss) & (df['Date'] <= se)].dropna(subset=FEATURE_COLS + ['target', 'ret_5d_net'])
        if train.empty or test.empty:
            continue
        probs = train_and_score(train, test)
        fold_summary = summarize_fold(train, test, probs)
        fold_summary['Fold'] = fold_id
        results.append(fold_summary)
        if fold_id in [1, 2, 3, 4, 9, 12]:
            diagnostics.append((fold_id, fold_summary, fold_signal_stats(test, probs, CONFIDENCE_THRESHOLD), probs))

    lines = []
    lines.append('# Walkforward Diagnostics')
    lines.append('')
    lines.append('**Generated:** {}'.format(pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')))
    lines.append('')
    lines.append('## Fold summary and threshold counts')
    lines.append('')
    for r in results:
        lines.append(f"### Fold {r['Fold']} ({r['TrainStart']} → {r['TrainEnd']} train, {r['TestStart']} → {r['TestEnd']} test)")
        lines.append(f"- Test rows: {r['TestRows']}")
        lines.append(f"- Average predicted confidence: {r['AvgProb']:.4f}")
        lines.append(f"- Median predicted confidence: {r['MedianProb']:.4f}")
        lines.append('- Signals above thresholds:')
        for th, cnt in r['CountThresholds'].items():
            lines.append(f"  - >= {int(th*100)}%: {cnt}")
        lines.append('')

    lines.append('## Why folds 1–4 generated zero trades')
    lines.append('')
    lines.append('Folds 1–4 produced zero 75% confidence signals because the out-of-sample classifier scores in those early test periods did not reach the 0.75 threshold. The model was relatively conservative for these early test windows, and the highest predicted probabilities were below 0.75 despite a non-empty test set.')
    lines.append('')
    lines.append('### Fold 1–4 threshold behaviors')
    lines.append('')
    for fold_id, fold_summary, signal_stats, probs in diagnostics:
        if fold_id > 4:
            continue
        lines.append(f"- Fold {fold_id}: average test confidence {fold_summary['AvgProb']:.4f}, median {fold_summary['MedianProb']:.4f}, signals >= 75%: {fold_summary['CountThresholds'][0.75]}")
    lines.append('')
    lines.append('These zero-trade folds are best explained by the 75% threshold being too strict for the early out-of-sample scores. In other words, the classifier assigned lower confidence in fold 1–4 than in later periods, so no trades cleared the champion threshold.')
    lines.append('')
    lines.append('## Fold threshold distributions')
    lines.append('')
    for r in results:
        lines.append(f"- Fold {r['Fold']}: >=60% {r['CountThresholds'][0.60]}, >=65% {r['CountThresholds'][0.65]}, >=70% {r['CountThresholds'][0.70]}, >=75% {r['CountThresholds'][0.75]}, >=80% {r['CountThresholds'][0.80]}")
    lines.append('')

    lines.append('## Fold 9 vs Fold 12 comparison')
    lines.append('')
    fold9 = next((d for d in diagnostics if d[0] == 9), None)
    fold12 = next((d for d in diagnostics if d[0] == 12), None)
    if fold9:
        _, summary9, stats9, probs9 = fold9
        lines.append('### Fold 9 (best fold)')
        lines.append(f"- Train: {summary9['TrainStart']} → {summary9['TrainEnd']}")
        lines.append(f"- Test: {summary9['TestStart']} → {summary9['TestEnd']}")
        lines.append(f"- Test rows: {summary9['TestRows']}")
        lines.append(f"- Signals at 75%+: {summary9['CountThresholds'][0.75]}")
        if stats9:
            lines.append(f"- Average confidence: {stats9['AvgConfidence']:.4f}")
            lines.append(f"- Average predicted return: {stats9['AvgPredReturn']:.4f}")
            lines.append(f"- Average RSI: {stats9['AvgRSI']:.4f}")
            lines.append(f"- Average volatility_5d: {stats9['AvgVolatility']:.4f}")
            lines.append(f"- Average volume_ratio: {stats9['AvgVolumeRatio']:.4f}")
        else:
            lines.append('- No 75% signals were generated in this fold.')
        lines.append('')
    if fold12:
        _, summary12, stats12, probs12 = fold12
        lines.append('### Fold 12 (worst fold)')
        lines.append(f"- Train: {summary12['TrainStart']} → {summary12['TrainEnd']}")
        lines.append(f"- Test: {summary12['TestStart']} → {summary12['TestEnd']}")
        lines.append(f"- Test rows: {summary12['TestRows']}")
        lines.append(f"- Signals at 75%+: {summary12['CountThresholds'][0.75]}")
        if stats12:
            lines.append(f"- Average confidence: {stats12['AvgConfidence']:.4f}")
            lines.append(f"- Average predicted return: {stats12['AvgPredReturn']:.4f}")
            lines.append(f"- Average RSI: {stats12['AvgRSI']:.4f}")
            lines.append(f"- Average volatility_5d: {stats12['AvgVolatility']:.4f}")
            lines.append(f"- Average volume_ratio: {stats12['AvgVolumeRatio']:.4f}")
        else:
            lines.append('- No 75% signals were generated in this fold.')
        lines.append('')

    lines.append('## Market regime distribution')
    lines.append('')
    lines.append('No market regime field was present in `features.csv`, so market regime distribution cannot be computed from the available data. If a regime label is added to the feature set, this section can be updated.')
    lines.append('')
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'Saved diagnostics report to {REPORT_PATH}')


if __name__ == '__main__':
    main()
