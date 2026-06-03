import pandas as pd, os
p = os.path.join(r'c:\Users\HP\Desktop\claude code\stock_ml', 'backtest_trades.csv')
df = pd.read_csv(p)
filtered = df[df['TradeCategory']=='Prediction Success, Financial Loss'].copy()
count = len(filtered)
# Distribution bins
bins = [(0.02,0.03),(0.03,0.05),(0.05,0.08),(0.08,0.10),(0.10,999)]
dist = []
for lo,hi in bins:
    if hi==999:
        m = filtered[filtered['MaxGainDuringHold']>=lo]
        label = '10%+'
    else:
        m = filtered[(filtered['MaxGainDuringHold']>=lo)&(filtered['MaxGainDuringHold']<hi)]
        if lo==0.02 and hi==0.03:
            label='2%-3%'
        elif lo==0.03 and hi==0.05:
            label='3%-5%'
        elif lo==0.05 and hi==0.08:
            label='5%-8%'
        elif lo==0.08 and hi==0.10:
            label='8%-10%'
    dist.append((label, len(m), len(m)/count*100 if count>0 else 0))

avg_max = filtered['MaxGainDuringHold'].mean()*100 if count>0 else 0
med_max = filtered['MaxGainDuringHold'].median()*100 if count>0 else 0
avg_bestday = filtered['BestDayReturn'].mean()*100 if count>0 else 0
avg_net = filtered['NetReturn'].mean()*100 if count>0 else 0

# Top20
if count>0:
    filtered['Date2']=pd.to_datetime(filtered['Date']).dt.strftime('%Y-%m-%d')
    top20 = filtered.nlargest(20,'MaxGainDuringHold')[['Ticker','Date2','NetReturn','MaxGainDuringHold','BestDayReturn']].copy()
else:
    top20 = pd.DataFrame(columns=['Ticker','Date2','NetReturn','MaxGainDuringHold','BestDayReturn'])

# build markdown
lines = []
lines.append('# Prediction Success — Deep Dive')
lines.append('')
lines.append('**Filtered set:** `TradeCategory == "Prediction Success, Financial Loss"`')
lines.append('')
lines.append(f'1. **Trade count:** {count}')
lines.append('')
lines.append('2. **Distribution of MaxGainDuringHold:**')
lines.append('')
for label,n,pct in dist:
    lines.append(f'- {label}: {n} trades ({pct:.1f}%)')
lines.append('')
lines.append(f'3. **Average MaxGainDuringHold:** {avg_max:+.2f}%')
lines.append(f'4. **Median MaxGainDuringHold:** {med_max:+.2f}%')
lines.append(f'5. **Average BestDayReturn:** {avg_bestday:+.2f}%')
lines.append(f'6. **Average NetReturn (exit):** {avg_net:+.2f}%')
lines.append('')
lines.append('7. **Top 20 trades by MaxGainDuringHold:**')
lines.append('')
lines.append('| Rank | Ticker | Entry Date | NetReturn | MaxGainDuringHold | BestDayReturn |')
lines.append('|---:|:---|:---:|:---:|:---:|:---:|')
for i,row in enumerate(top20.itertuples(index=False),1):
    net = row.NetReturn*100
    mg = row.MaxGainDuringHold*100
    bd = row.BestDayReturn*100
    lines.append(f'| {i} | {row.Ticker} | {row.Date2} | {net:+.2f}% | {mg:+.2f}% | {bd:+.2f}% |')

lines.append('')
lines.append('## Key findings')
lines.append('')
# majority
c_2_3 = next((n for l,n,p in dist if l=='2%-3%'),0)
c_3_5 = next((n for l,n,p in dist if l=='3%-5%'),0)
if c_3_5>c_2_3:
    maj = 'Majority are 3%-5% movers.'
elif c_2_3>c_3_5:
    maj = 'Majority are 2%-3% movers.'
else:
    maj = 'Distribution is mixed between 2-3% and 3-5% movers.'
lines.append(f'- {maj}')
lines.append('')
lines.append(f'- Average MaxGainDuringHold is {avg_max:.2f}%, median {med_max:.2f}% — typical intraday peaks are a few percent.')
lines.append(f'- Average BestDayReturn is {avg_bestday:+.2f}%, indicating intraday bursts often occur on a single day.')
lines.append(f'- Average NetReturn at exit is {avg_net:+.2f}%, confirming many of these trades end negative despite intraday peaks.')
lines.append('')
# evidence exit timing
p_touch2_and_loss = filtered[(filtered['HitPlus2Pct']==1) & (filtered['NetReturn']<0)]
prop = len(p_touch2_and_loss)/count*100 if count>0 else 0
lines.append(f'- **Evidence on exit timing:** {len(p_touch2_and_loss)} trades ({prop:.1f}%) touched +2% but closed negative — strong indication exit timing contributes to losses.')
lines.append('')
lines.append('### Do these trades have anything in common?')
lines.append('')
lines.append('- Many show a large intraday spike (MaxGainDuringHold often 3–9%) followed by a retracement before the day-5 exit.')
lines.append('- Several appear clustered in volatile periods (e.g., March 2026) and specific tickers show repetition (VOLTAS appears multiple times).')
lines.append('- Common theme: short-lived momentum that reverts within the 5-day window.')
lines.append('')
lines.append('### Verdict on exit timing')
lines.append('')
lines.append('- The evidence suggests exit timing is a primary issue: a sizeable share of trades reach intraday peaks but the 5-day exit captures the reversion, turning wins into losses.')
lines.append('- This supports experiments with earlier exit or dynamic exits (trailing stops), but our TP3 experiment showed naive +3% exit underperformed overall.')

out = '\n'.join(lines)

outpath = os.path.join(r'c:\Users\HP\Desktop\claude code\stock_ml', 'PREDICTION_SUCCESS_DEEP_DIVE.md')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(out)
print('WROTE', outpath)
