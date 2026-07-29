import pandas as pd
from pipeline_core import load_price_series, engine
import linear_rank_allocator
import inverse_volatility_allocator
from eval_engine import PredictionAdapter, PortfolioConstructor, ModelAgnosticSimulator

# Load predictions and adapt to required format (classifier style)
preds_path = 'test_predictions.csv'
df_raw = pd.read_csv(preds_path)
df_raw['Date'] = pd.to_datetime(df_raw['Date'])
adapted = PredictionAdapter.adapt_classifier(df_raw)

# Load price series
prices = load_price_series()

# Fixed parameters for benchmark
K = 10  # top‑K portfolio selection

def compute_weights_by_day(predictions, allocator_name):
    """Return a dict of date -> {ticker: weight} using the requested allocator."""
    weights_by_day = {}
    for date, df_day in predictions.groupby('Date'):
        weights = engine.allocate(df_day, strategy=allocator_name, date=date)
        if weights:
            weights_by_day[pd.Timestamp(date)] = weights
    return weights_by_day

def run_benchmark(allocator_name):
    # Build trades for top‑K using the same predictions (rank already present)
    trades = PortfolioConstructor.construct_top_k_trades(adapted, prices, K)
    # Only pass the Top-K portfolio to the allocator!
    top_k_preds = adapted[adapted['Rank'] <= K]
    # Compute daily weights according to allocator
    weights_by_day = compute_weights_by_day(top_k_preds, allocator_name)
    # Simulate with the weight dict
    port, cagr, sharpe, max_dd, win_rate, avg_ret, n = ModelAgnosticSimulator.simulate(
        trades, prices, weights_by_day=weights_by_day
    )
    # Total return as percentage (same as portfolio return printed by back‑test)
    total_return = (port['TotalValue'].iloc[-1] - 100_000) / 100_000 * 100 if n else 0.0
    return {
        'Total Return %': total_return,
        'CAGR %': cagr * 100,
        'Sharpe': sharpe,
        'Max Drawdown %': max_dd * 100,
        'Win Rate %': win_rate * 100,
        'Avg Trade Return %': avg_ret * 100,
        'Number of Trades': n,
    }

if __name__ == "__main__":
    results = {}
    for name in ["equal_weight", "linear_rank", "inverse_volatility"]:
        print(f"Running benchmark for allocator: {name}")
        results[name] = run_benchmark(name)
    # Print markdown table
    print("\n# Allocator Comparison")
    print("| Metric | Equal Weight | Linear Rank | Inverse Vol |")
    print("|---|---|---|---|")
    metrics = [
        'Total Return %', 'CAGR %', 'Sharpe', 'Max Drawdown %',
        'Win Rate %', 'Avg Trade Return %', 'Number of Trades'
    ]
    for m in metrics:
        eq = results['equal_weight'][m]
        lr = results['linear_rank'][m]
        iv = results['inverse_volatility'][m]
        # format numbers nicely
        if isinstance(eq, float):
            print(f"| {m} | {eq:.4f} | {lr:.4f} | {iv:.4f} |")
        else:
            print(f"| {m} | {eq} | {lr} | {iv} |")
