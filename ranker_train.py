#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
FEATURE_FILE = ROOT / 'features.csv'

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
    
    # Train on first 24 months
    min_date = df['Date'].min()
    train_end = min_date + pd.DateOffset(months=24)
    train = df[(df['Date'] <= train_end)].dropna(subset=valid_features)
    
    if len(train) == 0:
        print("No training data.")
        return
        
    print(f"Training XGBRanker on {len(train)} rows...")
    
    # Create QID
    # XGBRanker requires data to be sorted by QID
    train = train.sort_values(by=['Date', 'ticker'])
    train['qid'] = train.groupby('Date').ngroup()
    
    X_train = train[valid_features]
    y_train = train['target']
    qid_train = train['qid']
    
    # Map target to relevance score (binary target -> 0 or 1 relevance is fine for ndcg)
    
    ranker = xgb.XGBRanker(
        tree_method="hist",
        objective="rank:ndcg",
        eval_metric="ndcg",
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_estimators=100
    )
    
    ranker.fit(
        X_train, y_train, qid=qid_train,
        verbose=True
    )
    
    print("Ranker training completed.")
    ranker.save_model("ranker_model.json")
    print("Saved ranker_model.json")

if __name__ == "__main__":
    main()
