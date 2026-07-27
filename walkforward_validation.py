#!/usr/bin/env python3
"""
Walk-forward validation pipeline for the Stock ML strategy.

- Rolling window validation
- 24-month train
- 3-month test
- 5-trading-day gap between train and test
- Quarterly retraining

This script creates:
- walkforward_results.csv
- WALKFORWARD_REPORT.md
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import warnings
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, roc_auc_score, mean_squared_error
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parent
FEATURE_FILE = ROOT / 'features.csv'
DATA_DIR = ROOT / 'data'
RESULTS_CSV = ROOT / 'walkforward_results.csv'
REPORT_MD = ROOT / 'WALKFORWARD_REPORT.md'

# Columns that must never be used as predictors
EXCLUDED_FEATURES = {
    'Date', 'ticker', 'target', 'future_ret_5d', 'ret_5d_net',
    'Open', 'High', 'Low', 'Close', 'Volume',
    'high_52w', 'low_52w',
}

# Auto-discover every numeric predictor from the CSV header
df_cols_full = pd.read_csv(FEATURE_FILE, nrows=1)
numeric_cols_all = df_cols_full.select_dtypes(include='number').columns.tolist()
FEATURE_COLS = [col for col in numeric_cols_all if col not in EXCLUDED_FEATURES]

print(f"Walkforward feature count: {len(FEATURE_COLS)}")

CONFIDENCE_THRESHOLD = 0.75
HOLD_DAYS = 5
MAX_POSITIONS = 10
BROKERAGE = 0.001
SLIPPAGE = 0.002
TOTAL_COST = BROKERAGE + SLIPPAGE
STARTING_CAPITAL = 100_000
TRAIN_MONTHS = 24
TEST_MONTHS = 3
GAP_DAYS = 6
STEP_MONTHS = 3


def load_feature_data():
    df = pd.read_csv(FEATURE_FILE)
    df['Date'] = pd.to_datetime(df['Date'])
    return df


def load_price_series():
    prices = {}
    for f in DATA_DIR.glob('*.csv'):
        try:
            p = pd.read_csv(f, index_col=0)
            p.index = pd.to_datetime(p.index)
            if 'Adj Close' in p.columns:
                prices[f.stem] = p['Adj Close'].sort_index()
            elif 'Close' in p.columns:
                prices[f.stem] = p['Close'].sort_index()
        except Exception:
            continue
    return prices


def compute_hold_path_metrics(hold_prices, entry_price, net_return):
    hold = np.asarray(hold_prices, dtype=float)
    if len(hold) < 2 or entry_price <= 0:
        return None
    cum_ret = hold / entry_price - 1.0
    day_ret = np.diff(hold) / hold[:-1]
    running_max = np.maximum.accumulate(cum_ret)
    drawdowns = cum_ret - running_max
    max_gain = float(cum_ret.max())
    max_dd = float(drawdowns.min())
    mae = float(cum_ret.min())
    best_day = float(day_ret.max()) if len(day_ret) else 0.0
    worst_day = float(day_ret.min()) if len(day_ret) else 0.0
    was_profitable_intraday = max_gain > 0
    loser_but_green = net_return < 0 and was_profitable_intraday
    return {
        'MaxGainDuringHold':       max_gain,
        'MaxDrawdownDuringHold':   max_dd,
        'MaxAdverseExcursion':     mae,
        'BestDayReturn':           best_day,
        'WorstDayReturn':          worst_day,
        'HitPlus2Pct':             int(max_gain >= 0.02),
        'HitPlus3Pct':             int(max_gain >= 0.03),
        'HitPlus5Pct':             int(max_gain >= 0.05),
        'WasProfitableIntraday':   int(was_profitable_intraday),
        'LoserButProfitableIntraday': int(loser_but_green),
    }


def build_trade_df(signals, prices):
    trades = []
    for _, row in signals.iterrows():
        ticker = row['ticker']
        entry_date = row['Date']
        if ticker not in prices:
            continue
        stock_prices = prices[ticker]
        future_dates = stock_prices[stock_prices.index > entry_date]
        if len(future_dates) < HOLD_DAYS + 1:
            continue
        hold_prices = future_dates.iloc[0:HOLD_DAYS + 1]
        entry_price = hold_prices.iloc[0]
        exit_price = hold_prices.iloc[HOLD_DAYS]
        gross_return = (exit_price - entry_price) / entry_price
        net_return = gross_return - TOTAL_COST
        path_metrics = compute_hold_path_metrics(hold_prices.values, entry_price, net_return)
        if path_metrics is None:
            continue
        trades.append({
            'Date':        future_dates.index[0],
            'SignalDate':  entry_date,
            'Ticker':      ticker,
            'Confidence':  row['xg_proba'],
            'PredReturn':  row.get('pred_return', np.nan),
            'EntryPrice':  entry_price,
            'ExitPrice':   exit_price,
            'GrossReturn': gross_return,
            'NetReturn':   net_return,
            'Won':         int(net_return > 0),
            **path_metrics,
        })
    return pd.DataFrame(trades)


def get_price_on_date(price_series, date):
    if date in price_series.index:
        return float(price_series.loc[date])
    prior = price_series[price_series.index < date]
    if len(prior) == 0:
        return None
    return float(prior.iloc[-1])


def get_position_size(confidence):
    if confidence >= 0.85:
        return 0.15
    if confidence >= 0.80:
        return 0.125
    return 0.10


def simulate_portfolio(trades_df, prices, rank_by_pred_return=False):
    cash = STARTING_CAPITAL
    locked_cash = 0.0
    realized_pnl = 0.0
    portfolio_history = []
    open_positions = []
    entry_buckets = {}
    if len(trades_df) == 0:
        return pd.DataFrame(columns=['Date','Cash','LockedCash','UnrealizedValue','TotalValue','Value','Drawdown']), 0.0, 0.0
    max_exit_date = trades_df['Date'].max()
    for date, day_trades in trades_df.groupby('Date'):
        if rank_by_pred_return and 'PredReturn' in day_trades.columns:
            entry_buckets[date] = day_trades.sort_values('PredReturn', ascending=False).head(MAX_POSITIONS)
        else:
            entry_buckets[date] = day_trades.sort_values('Confidence', ascending=False).head(MAX_POSITIONS)
    for date, day_trades in entry_buckets.items():
        day_trades = day_trades.copy()
        for idx, t in day_trades.iterrows():
            price_index = prices[t['Ticker']].index
            pos = price_index.get_indexer([t['Date']])[0]
            exit_date = price_index[pos + HOLD_DAYS]
            max_exit_date = max(max_exit_date, exit_date)
            day_trades.loc[idx, 'ExitDate'] = exit_date
        entry_buckets[date] = day_trades
    calendar_dates = sorted({d for ticker in trades_df['Ticker'].unique() if ticker in prices for d in prices[ticker].index})
    calendar_dates = [d for d in calendar_dates if d >= trades_df['Date'].min() and d <= max_exit_date]
    for today in calendar_dates:
        exits = [p for p in open_positions if p['ExitDate'] == today]
        for pos in exits:
            pnl = pos['LockedCash'] * pos['NetReturn']
            cash += pos['LockedCash'] + pnl
            locked_cash -= pos['LockedCash']
            realized_pnl += pnl
            open_positions.remove(pos)
        if today in entry_buckets and len(open_positions) < MAX_POSITIONS:
            for _, t in entry_buckets[today].iterrows():
                if len(open_positions) >= MAX_POSITIONS:
                    break
                available_cash = cash
                if available_cash <= 0:
                    break
                position_size = get_position_size(t['Confidence'])
                locked_amount = min(
                    available_cash,
                    (cash + sum(get_price_on_date(prices[pos['Ticker']], today) * pos['Quantity'] for pos in open_positions)) * position_size
                )
                if locked_amount <= 0:
                    break
                quantity = locked_amount / t['EntryPrice']
                open_positions.append({
                    'Ticker':      t['Ticker'],
                    'EntryDate':   t['Date'],
                    'ExitDate':    t['ExitDate'],
                    'EntryPrice':  t['EntryPrice'],
                    'ExitPrice':   t['ExitPrice'],
                    'Quantity':    quantity,
                    'LockedCash':  locked_amount,
                    'NetReturn':   t['NetReturn'],
                    'Confidence':  t['Confidence'],
                })
                cash -= locked_amount
                locked_cash += locked_amount
        unrealized_value = 0.0
        for pos in open_positions:
            current_price = get_price_on_date(prices[pos['Ticker']], today)
            if current_price is None:
                current_price = pos['EntryPrice']
            unrealized_value += pos['Quantity'] * current_price
        total_value = cash + unrealized_value
        portfolio_history.append({
            'Date': today,
            'Cash': cash,
            'LockedCash': locked_cash,
            'UnrealizedValue': unrealized_value,
            'TotalValue': total_value,
        })
    port_df = pd.DataFrame(portfolio_history)
    if len(port_df) > 0:
        port_df['Value'] = port_df['TotalValue']
        port_df['Drawdown'] = port_df['TotalValue'] / port_df['TotalValue'].cummax() - 1
        total_return = (port_df['TotalValue'].iloc[-1] - STARTING_CAPITAL) / STARTING_CAPITAL * 100
        max_dd = port_df['Drawdown'].min() * 100
    else:
        total_return = 0.0
        max_dd = 0.0
    return port_df, total_return, max_dd


def get_fold_boundaries(dates):
    """Generate walk‑forward fold boundaries.

    ``dates`` can be a list, ``pd.Series`` or ``pd.DatetimeIndex`` of sorted dates.
    The function now uses positional indexing (``iloc``) to avoid pandas label‑based
    lookup issues that caused ``KeyError: -1`` when the series was indexed with
    negative numbers.
    """
    # Ensure we have a proper DatetimeIndex for reliable positional indexing
    dates = pd.DatetimeIndex(dates)

    folds = []
    min_date = dates[0]
    max_date = dates[-1]
    train_start = min_date
    while True:
        # Desired end of the training window (inclusive)
        train_end_target = train_start + pd.DateOffset(months=TRAIN_MONTHS) - pd.Timedelta(days=1)
        # Locate the last date <= target using searchsorted (returns position)
        pos = dates.searchsorted(train_end_target, side='right') - 1
        if pos < 0:
            break
        train_end = dates[pos]
        if train_end < train_start:
            break
        train_end_idx = pos
        test_start_idx = train_end_idx + GAP_DAYS + 1
        if test_start_idx >= len(dates):
            break
        test_start = dates[test_start_idx]
        test_end_target = test_start + pd.DateOffset(months=TEST_MONTHS) - pd.Timedelta(days=1)
        if test_end_target > max_date:
            break
        test_end_pos = dates.searchsorted(test_end_target, side='right') - 1
        if test_end_pos < test_start_idx:
            break
        test_end = dates[test_end_pos]
        folds.append({
            'train_start': train_start,
            'train_end': train_end,
            'test_start': test_start,
            'test_end': test_end,
        })
        # Move the training window forward
        train_start = train_start + pd.DateOffset(months=STEP_MONTHS)
        if train_start > max_date:
            break
    return folds


def fold_metrics(trades_df):
    if len(trades_df) == 0:
        return {
            'Trades': 0,
            'WinRate_%': np.nan,
            'PredictionSuccessRate_%': np.nan,
            'PortfolioReturn_%': np.nan,
            'MaxDrawdown_%': np.nan,
        }
    return {
        'Trades': len(trades_df),
        'WinRate_%': float(trades_df['Won'].mean() * 100),
        'PredictionSuccessRate_%': float(trades_df['HitPlus2Pct'].mean() * 100),
        'PortfolioReturn_%': float(trades_df['PortfolioReturn_%'].iloc[0]),
        'MaxDrawdown_%': float(trades_df['MaxDrawdown_%'].iloc[0]),
    }


def run_walkforward():
    print('Loading feature data...')
    df = load_feature_data()
    print('Loading price series...')
    prices = load_price_series()
    dates = pd.DatetimeIndex(np.sort(df['Date'].unique()))
    folds = get_fold_boundaries(dates)
    print(f'Found {len(folds)} walk-forward folds')
    results = []
    for idx, fold in enumerate(folds, start=1):
        print(f"\nFold {idx}: train {fold['train_start'].date()} -> {fold['train_end'].date()}, "
              f"gap {GAP_DAYS} days, test {fold['test_start'].date()} -> {fold['test_end'].date()}")
        train = df[(df['Date'] >= fold['train_start']) & (df['Date'] <= fold['train_end'])].dropna(subset=FEATURE_COLS + ['target', 'ret_5d_net'])
        test = df[(df['Date'] >= fold['test_start']) & (df['Date'] <= fold['test_end'])].dropna(subset=FEATURE_COLS + ['target', 'ret_5d_net'])
        if train.empty or test.empty:
            print('  Skipping fold because train or test set is empty')
            continue
        X_train = train[FEATURE_COLS]
        y_train = train['target']
        X_test = test[FEATURE_COLS]
        y_test = test['target']
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)
        # classifier
        scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        xg = xgb.XGBClassifier(
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
        xg.fit(X_train_s, y_train, eval_set=[(X_test_s, y_test)], verbose=False)
        xg_proba = xg.predict_proba(X_test_s)[:, 1]
        xg_pred_thr = (xg_proba >= CONFIDENCE_THRESHOLD).astype(int)
        xg_acc = accuracy_score(y_test, xg_proba >= 0.5)
        xg_prec = precision_score(y_test, xg_pred_thr, zero_division=0)
        xg_auc = roc_auc_score(y_test, xg_proba)
        # regressor
        y_train_reg = train['ret_5d_net']
        y_test_reg = test['ret_5d_net']
        xg_reg = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective='reg:squarederror',
            random_state=42,
            n_jobs=-1,
        )
        xg_reg.fit(X_train_s, y_train_reg, eval_set=[(X_test_s, y_test_reg)], verbose=False)
        pred_return = xg_reg.predict(X_test_s)
        test_out = test[['Date', 'ticker', 'target']].copy()
        test_out['xg_proba'] = xg_proba
        test_out['signal'] = xg_pred_thr
        test_out['pred_return'] = pred_return
        trades_df = test_out[test_out['signal'] == 1].copy()
        trades_df = trades_df.sort_values('Date')
        if not trades_df.empty:
            trades_df = build_trade_df(trades_df, prices)
        print(f'  Signals generated: {len(trades_df):,}')
        if len(trades_df) == 0:
            result = {
                'Fold': idx,
                'TrainStart': fold['train_start'].date(),
                'TrainEnd': fold['train_end'].date(),
                'TestStart': fold['test_start'].date(),
                'TestEnd': fold['test_end'].date(),
                'Trades': 0,
                'WinRate_%': np.nan,
                'PredictionSuccessRate_%': np.nan,
                'PortfolioReturn_%': np.nan,
                'MaxDrawdown_%': np.nan,
            }
            results.append(result)
            continue
        trades_df['PredictionSuccess'] = (trades_df['HitPlus2Pct'] == 1).astype(int)
        port_df, total_return, max_dd = simulate_portfolio(trades_df, prices, rank_by_pred_return=True)
        win_rate = trades_df['Won'].mean() * 100
        pred_success_rate = trades_df['PredictionSuccess'].mean() * 100
        result = {
            'Fold': idx,
            'TrainStart': fold['train_start'].date(),
            'TrainEnd': fold['train_end'].date(),
            'TestStart': fold['test_start'].date(),
            'TestEnd': fold['test_end'].date(),
            'Trades': len(trades_df),
            'WinRate_%': float(win_rate),
            'PredictionSuccessRate_%': float(pred_success_rate),
            'PortfolioReturn_%': float(total_return),
            'MaxDrawdown_%': float(max_dd),
            'Classifier_AUC': float(xg_auc),
            'Classifier_Precision_75%': float(xg_prec),
            'Regressor_RMSE': float(np.sqrt(mean_squared_error(y_test_reg, pred_return))),
        }
        results.append(result)
        print(f'  Portfolio return: {total_return:+.1f}%, Drawdown: {max_dd:+.1f}%, Win rate: {win_rate:.1f}%, Prediction success: {pred_success_rate:.1f}%')
    return pd.DataFrame(results)


def write_report(results_df):
    valid = results_df.dropna(subset=['Trades']).copy()
    n_folds = len(results_df)
    folds_with_trades = len(results_df[results_df['Trades'] > 0])
    avg_metrics = results_df[['Trades', 'WinRate_%', 'PredictionSuccessRate_%', 'PortfolioReturn_%', 'MaxDrawdown_%']].mean(skipna=True)
    std_metrics = results_df[['Trades', 'WinRate_%', 'PredictionSuccessRate_%', 'PortfolioReturn_%', 'MaxDrawdown_%']].std(skipna=True)
    best_fold = results_df.loc[results_df['PortfolioReturn_%'].idxmax()] if not results_df['PortfolioReturn_%'].dropna().empty else None
    worst_fold = results_df.loc[results_df['PortfolioReturn_%'].idxmin()] if not results_df['PortfolioReturn_%'].dropna().empty else None
    lines = []
    lines.append('# Walk-Forward Validation Report')
    lines.append('')
    lines.append(f'**Generated:** {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('')
    lines.append('## Summary')
    lines.append('')
    lines.append(f'- Total folds considered: **{n_folds}**')
    lines.append(f'- Folds with trades: **{folds_with_trades}**')
    lines.append(f'- Strategy threshold: **{CONFIDENCE_THRESHOLD:.0%}**')
    lines.append(f'- Train window: **{TRAIN_MONTHS} months**')
    lines.append(f'- Test window: **{TEST_MONTHS} months**')
    lines.append(f'- Gap between train/test: **{GAP_DAYS} trading days**')
    lines.append('')
    lines.append('## Fold metrics')
    lines.append('')
    lines.append('| Fold | Train | Test | Trades | Win Rate % | Prediction Success % | Portfolio Return % | Max Drawdown % |')
    lines.append('|---|---|---|---:|---:|---:|---:|---:|')
    for _, row in results_df.iterrows():
        lines.append(
            f"| {int(row['Fold'])} | {row['TrainStart']} → {row['TrainEnd']} | {row['TestStart']} → {row['TestEnd']} | "
            f"{int(row['Trades'])} | {row['WinRate_%']:.2f} | {row['PredictionSuccessRate_%']:.2f} | {row['PortfolioReturn_%']:.2f} | {row['MaxDrawdown_%']:.2f} |"
        )
    lines.append('')
    lines.append('## Average metrics')
    lines.append('')
    lines.append(f'- Average trade count: **{avg_metrics["Trades"]:.1f}**')
    lines.append(f'- Average win rate: **{avg_metrics["WinRate_%"]:.2f}%**')
    lines.append(f'- Average prediction success rate: **{avg_metrics["PredictionSuccessRate_%"]:.2f}%**')
    lines.append(f'- Average portfolio return: **{avg_metrics["PortfolioReturn_%"]:.2f}%**')
    lines.append(f'- Average max drawdown: **{avg_metrics["MaxDrawdown_%"]:.2f}%**')
    lines.append('')
    lines.append('## Standard deviation')
    lines.append('')
    lines.append(f'- Trade count stddev: **{std_metrics["Trades"]:.1f}**')
    lines.append(f'- Win rate stddev: **{std_metrics["WinRate_%"]:.2f}%**')
    lines.append(f'- Prediction success stddev: **{std_metrics["PredictionSuccessRate_%"]:.2f}%**')
    lines.append(f'- Portfolio return stddev: **{std_metrics["PortfolioReturn_%"]:.2f}%**')
    lines.append(f'- Max drawdown stddev: **{std_metrics["MaxDrawdown_%"]:.2f}%**')
    lines.append('')
    if best_fold is not None:
        lines.append('## Best fold')
        lines.append('')
        lines.append(f'- Fold **{int(best_fold["Fold"])}**: {best_fold["TrainStart"]} → {best_fold["TrainEnd"]} train, {best_fold["TestStart"]} → {best_fold["TestEnd"]} test')
        lines.append(f'- Portfolio return: **{best_fold["PortfolioReturn_%"]:.2f}%**')
        lines.append(f'- Win rate: **{best_fold["WinRate_%"]:.2f}%**')
        lines.append(f'- Prediction success: **{best_fold["PredictionSuccessRate_%"]:.2f}%**')
        lines.append(f'- Max drawdown: **{best_fold["MaxDrawdown_%"]:.2f}%**')
        lines.append('')
    if worst_fold is not None:
        lines.append('## Worst fold')
        lines.append('')
        lines.append(f'- Fold **{int(worst_fold["Fold"])}**: {worst_fold["TrainStart"]} → {worst_fold["TrainEnd"]} train, {worst_fold["TestStart"]} → {worst_fold["TestEnd"]} test')
        lines.append(f'- Portfolio return: **{worst_fold["PortfolioReturn_%"]:.2f}%**')
        lines.append(f'- Win rate: **{worst_fold["WinRate_%"]:.2f}%**')
        lines.append(f'- Prediction success: **{worst_fold["PredictionSuccessRate_%"]:.2f}%**')
        lines.append(f'- Max drawdown: **{worst_fold["MaxDrawdown_%"]:.2f}%**')
        lines.append('')
    lines.append('## Overall assessment')
    lines.append('')
    lines.append('This walk-forward validation evaluates the champion-style strategy on rolling, out-of-sample test windows with a realistic 5-day hold period and 5-trading-day separation from training data. The results above show how stable the strategy is across quarterly retraining folds, and identify whether the model generalizes consistently or suffers from fold-specific drawdowns.')
    lines.append('')
    lines.append('## Output files')
    lines.append('')
    lines.append('- `walkforward_results.csv`')
    lines.append('- `WALKFORWARD_REPORT.md`')
    lines.append('')
    lines.append('## Notes')
    lines.append('')
    lines.append('- This validation pipeline is separate from the champion strategy. It uses the same model configuration and portfolio simulator logic but operates on rolling train/test folds.')
    lines.append('- Folds with zero trades are included for transparency; their performance metrics are recorded as missing values.')
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'WALKFORWARD_REPORT.md saved -> {REPORT_MD}')


def main():
    results_df = run_walkforward()
    results_df.to_csv(RESULTS_CSV, index=False)
    print(f'walkforward_results.csv saved -> {RESULTS_CSV}')
    write_report(results_df)


if __name__ == '__main__':
    main()
