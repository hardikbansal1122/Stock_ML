import pandas as pd
import numpy as np
import os
import sys

trades_file = 'backtest_trades.csv'
if not os.path.exists(trades_file):
    print(f"No trades file {trades_file} found.")
    sys.exit(1)

df = pd.read_csv(trades_file)
if 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'])

results = []
hold_days = 5

for idx, row in df.iterrows():
    ticker = row['Ticker']
    signal_date = row['Date']
    
    data_file = f'data/{ticker}.csv'
    if not os.path.exists(data_file):
        continue
        
    price_df = pd.read_csv(data_file)
    if 'Date' in price_df.columns:
        price_df['Date'] = pd.to_datetime(price_df['Date'])
        price_df = price_df.set_index('Date')
    else:
        price_df.index = pd.to_datetime(price_df.index)
        
    price_df = price_df.sort_index()
    
    # Filter future prices strictly after signal_date
    future = price_df[price_df.index > signal_date]
    if len(future) < hold_days + 1:
        continue
        
    # Day 0 is entry, Day 1..hold_days are held
    trade_prices = future.iloc[0:hold_days+1]
    
    entry_date = trade_prices.index[0]
    exit_date = trade_prices.index[-1]
    
    entry_price = trade_prices['Close'].iloc[0]
    exit_price = trade_prices['Close'].iloc[-1]
    
    highest_high = trade_prices['High'].max()
    lowest_low = trade_prices['Low'].min()
    
    mfe = (highest_high - entry_price) / entry_price * 100
    mae = (lowest_low - entry_price) / entry_price * 100
    
    peak_idx = trade_prices['High'].argmax()
    bottom_idx = trade_prices['Low'].argmin()
    
    final_return = (exit_price - entry_price) / entry_price * 100
    
    res = {
        'Ticker': ticker,
        'Signal Date': signal_date.strftime('%Y-%m-%d'),
        'Entry Date': entry_date.strftime('%Y-%m-%d'),
        'Exit Date': exit_date.strftime('%Y-%m-%d'),
        'Entry Price': entry_price,
        'Exit Price': exit_price,
        'Highest High': highest_high,
        'Lowest Low': lowest_low,
        'MFE (%)': mfe,
        'MAE (%)': mae,
        'Day MFE occurred': peak_idx,
        'Day MAE occurred': bottom_idx,
        'Final Return (%)': final_return
    }
    results.append(res)

out_df = pd.DataFrame(results)
out_df.to_csv('trade_path_analysis.csv', index=False)

# Compute metrics
avg_mfe = out_df['MFE (%)'].mean()
avg_mae = out_df['MAE (%)'].mean()
pct_2 = (out_df['MFE (%)'] >= 2).mean() * 100
pct_3 = (out_df['MFE (%)'] >= 3).mean() * 100
pct_5 = (out_df['MFE (%)'] >= 5).mean() * 100
pct_8 = (out_df['MFE (%)'] >= 8).mean() * 100
pct_10 = (out_df['MFE (%)'] >= 10).mean() * 100
avg_day_max_profit = out_df['Day MFE occurred'].mean()

negative_trades = out_df[out_df['Final Return (%)'] < 0]
neg_but_5 = (negative_trades['MFE (%)'] >= 5).sum()
neg_but_8 = (negative_trades['MFE (%)'] >= 8).sum()

never_profitable = (out_df['MFE (%)'] <= 0).sum()

print("--- RESEARCH REPORT ---")
print(f"Total Trades: {len(out_df)}")
print(f"Average MFE: {avg_mfe:.2f}%")
print(f"Average MAE: {avg_mae:.2f}%")
print(f"Percentage of trades reaching +2%: {pct_2:.2f}%")
print(f"Percentage of trades reaching +3%: {pct_3:.2f}%")
print(f"Percentage of trades reaching +5%: {pct_5:.2f}%")
print(f"Percentage of trades reaching +8%: {pct_8:.2f}%")
print(f"Percentage of trades reaching +10%: {pct_10:.2f}%")
print(f"Average day of maximum profit: {avg_day_max_profit:.2f}")
print(f"Number of trades that finished negative but reached +5%: {neg_but_5}")
print(f"Number of trades that finished negative but reached +8%: {neg_but_8}")
print(f"Number of trades that never became profitable: {never_profitable}")
