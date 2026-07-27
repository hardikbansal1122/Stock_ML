#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import warnings
from pathlib import Path
from walkforward_validation import get_fold_boundaries, TRAIN_MONTHS, TEST_MONTHS, GAP_DAYS, STEP_MONTHS

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
FEATURE_FILE = ROOT / 'features.csv'
OUT_PREDS = ROOT / 'ranker_preds.csv'

BASELINE_FEATURES = [
    'price_vs_ma50', 'nifty_above_ma50', 'ma10_vs_ma50', 'ret_5d', 'ret_10d', 'ret_20d',
    'volatility_5d', 'volatility_20d', 'hl_range', 'bb_position', 'updown_vol_ratio_10', 
    'nifty_ret_5d', 'nifty_ret_20d'
]

def main():
    print("Loading features...")
    df = pd.read_csv(FEATURE_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    
    valid_features = [f for f in BASELINE_FEATURES if f in df.columns]
    print(f"Using {len(valid_features)} baseline features.")
    
    dates = pd.Series(df['Date'].unique()).sort_values().reset_index(drop=True)
    folds = get_fold_boundaries(dates)
    
    all_preds = []
    
    for idx, fold in enumerate(folds):
        train_start = fold['train_start']
        train_end = fold['train_end']
        test_start = fold['test_start']
        test_end = fold['test_end']
        print(f"\nFold {idx+1}/{len(folds)}: {train_start.date()} to {test_end.date()}")
        
        train = df[(df['Date'] >= train_start) & (df['Date'] <= train_end)].dropna(subset=valid_features)
        test = df[(df['Date'] >= test_start) & (df['Date'] <= test_end)].dropna(subset=valid_features)
        
        if len(train) == 0 or len(test) == 0: continue
        
        # Sort by Date for ranker
        train = train.sort_values(by=['Date', 'ticker'])
        test = test.sort_values(by=['Date', 'ticker'])
        
        train['qid'] = train.groupby('Date').ngroup()
        test['qid'] = test.groupby('Date').ngroup()
        
        X_train, y_train, qid_train = train[valid_features], train['target'], train['qid']
        X_test, y_test, qid_test = test[valid_features], test['target'], test['qid']
        
        # Train Classifier
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dtest = xgb.DMatrix(X_test, label=y_test)
        
        clf_params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 4,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'seed': 42
        }
        
        clf = xgb.train(clf_params, dtrain, num_boost_round=100, evals=[(dtest, 'test')], early_stopping_rounds=10, verbose_eval=False)
        clf_preds = clf.predict(dtest, iteration_range=(0, clf.best_iteration + 1))
        
        # Train Ranker
        ranker = xgb.XGBRanker(
            tree_method="hist",
            objective="rank:ndcg",
            eval_metric="ndcg",
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_estimators=100,
            early_stopping_rounds=10
        )
        
        ranker.fit(
            X_train, y_train, qid=qid_train,
            eval_set=[(X_test, y_test)], eval_qid=[qid_test],
            verbose=False
        )
        
        rnk_preds = ranker.predict(X_test)
        
        test_res = test[['Date', 'ticker', 'target', 'ret_5d_net']].copy()
        test_res['classifier_score'] = clf_preds
        test_res['ranker_score'] = rnk_preds
        
        all_preds.append(test_res)
        
    full_preds = pd.concat(all_preds)
    full_preds = full_preds.sort_values(['Date', 'ticker'])
    full_preds.to_csv(OUT_PREDS, index=False)
    print(f"\nWalkforward complete. Saved predictions to {OUT_PREDS.name}")

if __name__ == "__main__":
    main()
