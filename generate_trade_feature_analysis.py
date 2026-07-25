import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path('c:/Users/HP/Desktop/claude code/stock_ml')
REPORT_DIR = ROOT / 'trade_feature_analysis_outputs'
REPORT_DIR.mkdir(exist_ok=True)

trades = pd.read_csv(ROOT / 'backtest_trades.csv')
features = pd.read_csv(ROOT / 'features.csv')

# Normalize date/ticker columns for joining
for df in [trades, features]:
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date']).dt.normalize()

if 'ticker' in features.columns:
    features['ticker'] = features['ticker'].astype(str).str.strip().str.upper()
if 'Ticker' in trades.columns:
    trades['Ticker'] = trades['Ticker'].astype(str).str.strip().str.upper()

# Join features onto trades using Date + ticker/Ticker
merge_cols = ['Date']
if 'ticker' in features.columns and 'Ticker' in trades.columns:
    features = features.rename(columns={'ticker': 'Ticker'})
    merge_cols.append('Ticker')
elif 'Ticker' in features.columns and 'Ticker' in trades.columns:
    merge_cols.append('Ticker')

# Requested features
feature_names = ['rsi14', 'volatility_20d', 'ret_5d', 'ret_10d', 'ret_20d', 'rs_ret_60d', 'volume_ratio', 'Confidence']
available = [col for col in feature_names if col in features.columns or col in trades.columns]

# Merge with selected feature columns from features.csv
feature_frame = features[['Date', 'Ticker'] + [col for col in feature_names if col in features.columns]].copy()
merged = trades.merge(feature_frame, on=['Date', 'Ticker'], how='left')

# Use backtest confidence if present and features confidence absent
if 'Confidence' not in merged.columns:
    merged['Confidence'] = np.nan
elif 'Confidence_x' in merged.columns:
    merged['Confidence'] = merged['Confidence_x']
    merged.drop(columns=['Confidence_x','Confidence_y'], errors='ignore', inplace=True)

# Keep only rows with a valid outcome
merged = merged.dropna(subset=['Won', 'NetReturn']).copy()
merged['Won'] = merged['Won'].astype(int)

winner_mask = merged['Won'] == 1
loser_mask = merged['Won'] == 0

# Summary statistics by outcome
def summarize_feature(col: str):
    winners = merged.loc[winner_mask, col].dropna()
    losers = merged.loc[loser_mask, col].dropna()
    return pd.Series({
        'Feature': col,
        'Winners_mean': winners.mean(),
        'Losers_mean': losers.mean(),
        'Difference': winners.mean() - losers.mean(),
        'Winner_n': int(len(winners)),
        'Loser_n': int(len(losers)),
        'Winner_std': winners.std(ddof=0),
        'Loser_std': losers.std(ddof=0),
    })

summary_rows = []
for col in ['rsi14', 'volatility_20d', 'ret_5d', 'ret_10d', 'ret_20d', 'rs_ret_60d', 'volume_ratio', 'Confidence']:
    if col in merged.columns:
        summary_rows.append(summarize_feature(col))
summary_df = pd.DataFrame(summary_rows)

# Correlation with profit
correlation_rows = []
for col in ['rsi14', 'volatility_20d', 'ret_5d', 'ret_10d', 'ret_20d', 'rs_ret_60d', 'volume_ratio', 'Confidence']:
    if col in merged.columns:
        corr = merged[col].corr(merged['NetReturn'])
        correlation_rows.append({'Feature': col, 'Correlation_with_NetReturn': corr})
correlation_df = pd.DataFrame(correlation_rows).sort_values('Correlation_with_NetReturn', ascending=False)

# Top/bottom 20 trades
trade_summary = merged[['Date','Ticker','Confidence','NetReturn','GrossReturn','Won','rsi14','volatility_20d','ret_5d','ret_10d','ret_20d','rs_ret_60d','volume_ratio']].copy()
trade_summary = trade_summary.dropna(subset=['NetReturn', 'rsi14', 'volatility_20d', 'ret_5d', 'ret_10d', 'ret_20d', 'rs_ret_60d', 'volume_ratio'])
trade_summary_best = trade_summary.sort_values('NetReturn', ascending=False).head(20)
trade_summary_worst = trade_summary.sort_values('NetReturn', ascending=True).head(20)

# Distribution plots
plot_features = ['rsi14', 'volatility_20d', 'rs_ret_60d', 'Confidence']
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
for ax, feature in zip(axes.flatten(), plot_features):
    if feature not in merged.columns:
        continue
    winners = merged.loc[winner_mask, feature].dropna()
    losers = merged.loc[loser_mask, feature].dropna()
    if len(winners) and len(losers):
        ax.hist(winners, bins=30, alpha=0.6, label='Winner', density=True)
        ax.hist(losers, bins=30, alpha=0.6, label='Loser', density=True)
        ax.set_title(feature)
        ax.legend()
plt.tight_layout()
fig.savefig(REPORT_DIR / 'distribution_plots.png', dpi=200)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(correlation_df['Feature'], correlation_df['Correlation_with_NetReturn'])
ax.axhline(0, color='black', linewidth=0.8)
ax.set_title('Correlation with NetReturn')
ax.set_ylabel('Pearson correlation')
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
fig.savefig(REPORT_DIR / 'correlation_plot.png', dpi=200)
plt.close(fig)

# Interpretive ranking
summary_df = summary_df.sort_values('Difference', key=lambda s: s.abs(), ascending=False)
correlation_df = correlation_df.sort_values('Correlation_with_NetReturn', key=lambda s: s.abs(), ascending=False)

# Markdown
md_lines = []
md_lines.append('# Trade Feature Analysis')
md_lines.append('')
md_lines.append(f'- Source files: {ROOT / "backtest_trades.csv"} and {ROOT / "features.csv"}')
md_lines.append(f'- Total trades analyzed: {len(merged)}')
md_lines.append(f'- Winners: {int(winner_mask.sum())} | Losers: {int(loser_mask.sum())}')
md_lines.append('')
md_lines.append('## 1) Winning vs losing trade comparison')
md_lines.append('')
md_lines.append('| Feature | Winners mean | Losers mean | Difference | Winner n | Loser n |')
md_lines.append('|---|---:|---:|---:|---:|---:|')
for _, row in summary_df.iterrows():
    md_lines.append(f"| {row['Feature']} | {row['Winners_mean']:.4f} | {row['Losers_mean']:.4f} | {row['Difference']:.4f} | {int(row['Winner_n'])} | {int(row['Loser_n'])} |")
md_lines.append('')
md_lines.append('## 2) Distribution plots')
md_lines.append('')
md_lines.append(f'![Distribution plots]({REPORT_DIR.name}/distribution_plots.png)')
md_lines.append('')
md_lines.append('## 3) Correlation with profit')
md_lines.append('')
md_lines.append('| Feature | Correlation with NetReturn |')
md_lines.append('|---|---:|')
for _, row in correlation_df.iterrows():
    md_lines.append(f"| {row['Feature']} | {row['Correlation_with_NetReturn']:.4f} |")
md_lines.append('')
md_lines.append(f'![Correlation plot]({REPORT_DIR.name}/correlation_plot.png)')
md_lines.append('')
md_lines.append('## 4) Top 20 best trades')
md_lines.append('')
md_lines.append('| Rank | Date | Ticker | NetReturn | Confidence | RSI | Volatility | 5d ret | 10d ret | 20d ret | rs_ret_60d | Volume ratio |')
md_lines.append('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for idx, row in trade_summary_best.reset_index(drop=True).iterrows():
    md_lines.append(f"| {idx+1} | {row['Date'].date()} | {row['Ticker']} | {row['NetReturn']:.4f} | {row['Confidence']:.4f} | {row['rsi14']:.4f} | {row['volatility_20d']:.4f} | {row['ret_5d']:.4f} | {row['ret_10d']:.4f} | {row['ret_20d']:.4f} | {row['rs_ret_60d']:.4f} | {row['volume_ratio']:.4f} |")
md_lines.append('')
md_lines.append('## 5) Top 20 worst trades')
md_lines.append('')
md_lines.append('| Rank | Date | Ticker | NetReturn | Confidence | RSI | Volatility | 5d ret | 10d ret | 20d ret | rs_ret_60d | Volume ratio |')
md_lines.append('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
for idx, row in trade_summary_worst.reset_index(drop=True).iterrows():
    md_lines.append(f"| {idx+1} | {row['Date'].date()} | {row['Ticker']} | {row['NetReturn']:.4f} | {row['Confidence']:.4f} | {row['rsi14']:.4f} | {row['volatility_20d']:.4f} | {row['ret_5d']:.4f} | {row['ret_10d']:.4f} | {row['ret_20d']:.4f} | {row['rs_ret_60d']:.4f} | {row['volume_ratio']:.4f} |")
md_lines.append('')
md_lines.append('## 6) Summary')
md_lines.append('')
md_lines.append('### Features that clearly separate winners from losers')
for _, row in summary_df.head(5).iterrows():
    md_lines.append(f"- {row['Feature']}: winner mean {row['Winners_mean']:.4f} vs loser mean {row['Losers_mean']:.4f} (gap {row['Difference']:.4f})")
md_lines.append('')
md_lines.append('### Features that appear useless')
for _, row in correlation_df.tail(3).iterrows():
    md_lines.append(f"- {row['Feature']}: correlation with NetReturn = {row['Correlation_with_NetReturn']:.4f}")
md_lines.append('')
md_lines.append('### Features worth further research')
for _, row in correlation_df.head(5).iterrows():
    md_lines.append(f"- {row['Feature']}: correlation with NetReturn = {row['Correlation_with_NetReturn']:.4f}")
md_lines.append('')
md_lines.append('> This report is based on the current backtest trades export and the engineered feature matrix produced by the feature-building pipeline.')

REPORT_PATH = ROOT / 'trade_feature_analysis.md'
REPORT_PATH.write_text('\n'.join(md_lines), encoding='utf-8')
print('Wrote', REPORT_PATH)
print('Plots written to', REPORT_DIR)
