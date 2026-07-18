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
    
    # Filter future prices after signal_date
    future = price_df[price_df.index > signal_date]
    if len(future) < hold_days + 1:
        continue
        
    # Day 0 is entry, Day 1..hold_days are held
    trade_prices = future.iloc[0:hold_days+1]
    
    # Assuming entry price is the first close
    entry_price = trade_prices['Close'].iloc[0]
    
    # We analyze high/low across the hold period (Day 0 to Day 5)
    highest_high = trade_prices['High'].max()
    lowest_low = trade_prices['Low'].min()
    final_close = trade_prices['Close'].iloc[-1]
    
    peak_day = trade_prices['High'].idxmax().strftime('%Y-%m-%d')
    bottom_day = trade_prices['Low'].idxmin().strftime('%Y-%m-%d')
    
    if pd.notna(entry_price) and entry_price > 0:
        mfe = (highest_high - entry_price) / entry_price * 100
        mae = (lowest_low - entry_price) / entry_price * 100
    else:
        mfe = np.nan
        mae = np.nan
        
    res = {
        'Ticker': ticker,
        'Signal Date': signal_date.strftime('%Y-%m-%d'),
        'Entry Price': entry_price,
        'Highest High': highest_high,
        'Lowest Low': lowest_low,
        'Final Close': final_close,
        'MFE (%)': mfe,
        'MAE (%)': mae,
        'Peak Day': peak_day,
        'Bottom Day': bottom_day
    }
    results.append(res)

out_df = pd.DataFrame(results)
out_df.to_csv('historical_trades_analysis.csv', index=False)
print(f"Exported {len(out_df)} trades to historical_trades_analysis.csv")
