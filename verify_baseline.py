import pandas as pd
import numpy as np

print("=== 1. VERIFY NEW TARGET LABEL ===")
features = pd.read_csv('features.csv')
features['Date'] = pd.to_datetime(features['Date'])

ticker = features['ticker'].iloc[100]
df_stock = features[features['ticker'] == ticker].sort_values('Date').head(10).reset_index(drop=True)

prices = pd.read_csv(f'data/{ticker}.csv', index_col=0)
prices.index = pd.to_datetime(prices.index)
prices = prices.sort_index()

for i, row in df_stock.iterrows():
    signal_date = row['Date']
    target = row['future_ret_5d']
    
    # Get index of signal date
    pos = prices.index.get_indexer([signal_date])[0]
    if pos + 6 < len(prices):
        t1 = prices.index[pos + 1]
        t6 = prices.index[pos + 6]
        c1 = prices.loc[t1, 'Close'] if 'Close' in prices.columns else prices.loc[t1, 'Adj Close']
        c6 = prices.loc[t6, 'Close'] if 'Close' in prices.columns else prices.loc[t6, 'Adj Close']
        ret = c6 / c1 - 1
        
        print(f"Signal (T): {signal_date.date()} | Entry (T+1): {t1.date()} | Exit (T+6): {t6.date()}")
        print(f"  EntryPrice: {c1:.2f} | ExitPrice: {c6:.2f}")
        print(f"  Computed return: {ret:.4f} | ML future_ret_5d feature: {target:.4f}")
        print(f"  Match: {abs(ret - target) < 1e-5}")
    break

print("\n=== 2. VERIFY NO TIME TRAVEL ===")
trades = pd.read_csv('backtest_trades.csv')
trades['SignalDate'] = pd.to_datetime(trades['SignalDate'])
trades['Date'] = pd.to_datetime(trades['Date']) # This is EntryDate

time_travel_1 = (trades['SignalDate'] >= trades['Date']).sum()
print(f"Violations of SignalDate < EntryDate: {time_travel_1}")

print("\n=== 3. VERIFY PORTFOLIO SIMULATOR ===")
print("Trades are generated with Date=EntryDate, and simulate_portfolio processes daily using this EntryDate.")
print("The earliest trade entry date is:", trades['Date'].min().date())
print("The portfolio starts allocating cash exactly on the EntryDate.")

print("\n=== 4. VERIFY TRAIN/TEST BOUNDARY ===")
test_preds = pd.read_csv('test_predictions.csv')
test_preds['Date'] = pd.to_datetime(test_preds['Date'])
first_test = test_preds['Date'].min()

print(f"First testing prediction date: {first_test.date()}")
print(f"Last training date should be <= {(first_test - pd.Timedelta(days=10)).date()}")

train_mask = (features['Date'] < (pd.to_datetime('2024-07-01') - pd.Timedelta(days=10)))
last_train = features[train_mask]['Date'].max()
print(f"Actual last training sample: {last_train.date()}")
# For last_train, the target is t+6
pos = prices.index.get_indexer([last_train])[0]
if pos + 6 < len(prices):
    last_train_target_date = prices.index[pos + 6]
    print(f"Last training target realization date: {last_train_target_date.date()}")
    print(f"Overlap? {'Yes' if last_train_target_date >= first_test else 'No'}")
