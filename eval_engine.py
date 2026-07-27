import pandas as pd
import numpy as np

HOLD_DAYS = 5
TOTAL_COST = 0.001 + 0.002 # Brokerage + Slippage
STARTING_CAPITAL = 100_000
MAX_POSITIONS = 10
POSITION_SIZE = 0.10

class ValidationLayer:
    @staticmethod
    def validate_predictions(df):
        required_cols = ['Ticker', 'Date', 'Score', 'Rank']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required prediction column: {col}")
        if df['Score'].isnull().any():
            raise ValueError("Score column contains nulls.")

    @staticmethod
    def validate_trades(df):
        required_cols = ['Ticker', 'EntryDate', 'ExitDate', 'EntryPrice', 'ExitPrice', 'NetReturn', 'Score', 'Rank']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required trade column: {col}")


class PredictionAdapter:
    @staticmethod
    def adapt_classifier(df):
        df = df.copy()
        if 'classifier_score' in df.columns:
            df['Score'] = df['classifier_score']
        elif 'xg_proba' in df.columns:
            df['Score'] = df['xg_proba']
        else:
            raise ValueError("Classifier prediction must have 'xg_proba' or 'classifier_score'")
        
        if 'ticker' in df.columns:
            df = df.rename(columns={'ticker': 'Ticker'})
            
        df['Rank'] = df.groupby('Date')['Score'].rank(ascending=False, method='first')
        return df[['Ticker', 'Date', 'Score', 'Rank', 'target']]

    @staticmethod
    def adapt_ranker(df):
        df = df.copy()
        if 'ranker_score' in df.columns:
            df['Score'] = df['ranker_score']
        else:
            raise ValueError("Ranker prediction must have 'ranker_score'")
        if 'ticker' in df.columns:
            df = df.rename(columns={'ticker': 'Ticker'})
        df['Rank'] = df.groupby('Date')['Score'].rank(ascending=False, method='first')
        return df[['Ticker', 'Date', 'Score', 'Rank', 'target']]

class PortfolioConstructor:
    @staticmethod
    def construct_top_k_trades(predictions, prices, k):
        top_k_preds = predictions[predictions['Rank'] <= k]
        return PortfolioConstructor._build_trades(top_k_preds, prices)

    @staticmethod
    def construct_top_pct_trades(predictions, prices, pct):
        daily_counts = predictions.groupby('Date')['Ticker'].transform('count')
        top_pct_preds = predictions[predictions['Rank'] <= np.ceil(pct * daily_counts)]
        return PortfolioConstructor._build_trades(top_pct_preds, prices)

    @staticmethod
    def _build_trades(predictions, prices):
        trades = []
        for _, row in predictions.iterrows():
            ticker = row['Ticker']
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
            exit_date = future_dates.index[HOLD_DAYS]

            gross_return = (exit_price - entry_price) / entry_price
            net_return = gross_return - TOTAL_COST

            trades.append({
                'Ticker': ticker,
                'EntryDate': future_dates.index[0],
                'SignalDate': entry_date,
                'ExitDate': exit_date,
                'EntryPrice': entry_price,
                'ExitPrice': exit_price,
                'GrossReturn': gross_return,
                'NetReturn': net_return,
                'Won': int(net_return > 0),
                'Score': row['Score'],
                'Rank': row['Rank'],
            })

        return pd.DataFrame(trades)

def get_price_on_date(price_series, date):
    if date in price_series.index:
        return float(price_series.loc[date])
    prior = price_series[price_series.index < date]
    if len(prior) == 0:
        return None
    return float(prior.iloc[-1])

class ModelAgnosticSimulator:
    @staticmethod
    def simulate(trades_df, prices):
        if len(trades_df) == 0:
             return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0, 0.0, 0

        ValidationLayer.validate_trades(trades_df)
        
        cash = STARTING_CAPITAL
        locked_cash = 0.0
        portfolio_history = []
        open_positions = []

        entry_buckets = {}
        max_exit_date = trades_df['ExitDate'].max()
        
        for date, day_trades in trades_df.groupby('EntryDate'):
            entry_buckets[date] = day_trades.sort_values('Rank', ascending=True).head(MAX_POSITIONS)

        calendar_dates = sorted({d for ticker in trades_df['Ticker'].unique() if ticker in prices for d in prices[ticker].index})
        calendar_dates = [d for d in calendar_dates if d >= trades_df['EntryDate'].min() and d <= max_exit_date]

        for today in calendar_dates:
            exits = [p for p in open_positions if p['ExitDate'] == today]
            for pos in exits:
                pnl = pos['LockedCash'] * pos['NetReturn']
                cash += pos['LockedCash'] + pnl
                locked_cash -= pos['LockedCash']
                open_positions.remove(pos)

            if today in entry_buckets and len(open_positions) < MAX_POSITIONS:
                for _, t in entry_buckets[today].iterrows():
                    if len(open_positions) >= MAX_POSITIONS:
                        break
                    available_cash = cash
                    if available_cash <= 0:
                        break
                    
                    unrealized_sum = sum(get_price_on_date(prices[pos['Ticker']], today) * pos['Quantity'] for pos in open_positions)
                    nav = cash + unrealized_sum
                    
                    locked_amount = min(available_cash, nav * POSITION_SIZE)
                    if locked_amount <= 0:
                        break
                        
                    quantity = locked_amount / t['EntryPrice']
                    open_positions.append({
                        'Ticker':      t['Ticker'],
                        'ExitDate':    t['ExitDate'],
                        'EntryPrice':  t['EntryPrice'],
                        'Quantity':    quantity,
                        'LockedCash':  locked_amount,
                        'NetReturn':   t['NetReturn'],
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
                'PositionsOpen': len(open_positions),
            })

        port_df = pd.DataFrame(portfolio_history)
        if len(port_df) > 0:
            port_df['Value'] = port_df['TotalValue']
            port_df['Drawdown'] = port_df['TotalValue'] / port_df['TotalValue'].cummax() - 1
            total_return = (port_df['TotalValue'].iloc[-1] - STARTING_CAPITAL) / STARTING_CAPITAL
            max_dd = port_df['Drawdown'].min()
            
            years = (port_df['Date'].max() - port_df['Date'].min()).days / 365.25
            cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 and total_return > -1 else total_return
            
            daily_returns = port_df['TotalValue'].pct_change().dropna()
            sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if len(daily_returns) > 0 and daily_returns.std() > 0 else 0.0
            
            win_rate = trades_df['Won'].mean()
            avg_ret = trades_df['NetReturn'].mean()
        else:
            total_return = 0.0
            max_dd = 0.0
            cagr = 0.0
            sharpe = 0.0
            win_rate = 0.0
            avg_ret = 0.0

        return port_df, float(cagr), float(sharpe), float(max_dd), float(win_rate), float(avg_ret), len(trades_df)
