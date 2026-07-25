# Performance Audit: Run Model Inference Pipeline

Source files reviewed:
- [stock_dashboard/app.py](stock_dashboard/app.py)
- [stock_dashboard/auth_middleware.py](stock_dashboard/auth_middleware.py)
- [stock_dashboard/static/dashboard.html](stock_dashboard/static/dashboard.html)
- [step5_live_scanner.py](step5_live_scanner.py)

## Executive summary

The current bottleneck is not model inference. It is the per-ticker market-data download and feature recomputation that happens inside the scan request. The XGBoost model, scaler, and feature list are loaded once at startup, which is good. The slow part is the scan loop in [stock_dashboard/app.py](stock_dashboard/app.py), where the app downloads six months of data from yfinance for every ticker, recomputes indicators from scratch, runs prediction one stock at a time, and then writes results back to Supabase row by row.

For a user clicking Run Model, the architecture is therefore network-bound and sequential at the exact point where it should be batched and mostly cached.

## 1) Pipeline trace

### End-to-end flow

```mermaid
flowchart TD
    U[User clicks Run Model] --> B[dashboard.html runScan()]
    B --> A[fetchWithAuth adds Firebase token]
    A --> S1[GET /api/scan?threshold=...]
    S1 --> F[require_auth verifies Firebase token]
    F --> SB1[Supabase approved_users lookup]
    SB1 --> D[Duplicate scan check in user_scans]
    D --> R[run_scanner()]
    R --> T[Loop through universe tickers]
    T --> Y[yfinance.download 6mo history per ticker]
    Y --> FE[compute_features / feature engineering]
    FE --> L[Select FEATURE_COLS]
    L --> P[MODEL.predict_proba on one stock]
    P --> C[Threshold filter]
    C --> W1[Insert trades rows into Supabase]
    C --> W2[Insert scan_results rows into Supabase]
    C --> W3[Insert user_scans row]
    W1 --> J[Return JSON response]
    W2 --> J
    W3 --> J
    J --> UI[Browser renders signals]
```

### Actual execution path in the codebase

1. The dashboard page authenticates the user and fetches `/api/status` during bootstrap in [stock_dashboard/static/dashboard.html](stock_dashboard/static/dashboard.html).
2. The button handler `window.runScan()` calls `fetchWithAuth('/api/scan?threshold=...')` in [stock_dashboard/static/dashboard.html](stock_dashboard/static/dashboard.html).
3. `fetchWithAuth()` adds the Firebase ID token to the request headers.
4. The Flask route `/api/scan` in [stock_dashboard/app.py](stock_dashboard/app.py) is protected by `@require_auth` from [stock_dashboard/auth_middleware.py](stock_dashboard/auth_middleware.py).
5. `require_auth` verifies the Firebase token and checks the user against Supabase `approved_users`.
6. `/api/scan` checks whether the user already scanned today using Supabase `user_scans`.
7. The request enters `run_scanner()` in [stock_dashboard/app.py](stock_dashboard/app.py).
8. `run_scanner()` loops through the configured universe tickers.
9. For each ticker it calls `fetch_stock()`, which downloads market data from yfinance.
10. The code recomputes indicators and features via `compute_features()`.
11. The last row is extracted, aligned to `FEATURE_COLS`, and passed to `MODEL.predict_proba()`.
12. If the confidence exceeds the threshold, the signal is appended to the response and written into Supabase tables.
13. The API returns JSON and the browser updates the signal table.

## 2) Time complexity and runtime estimate

These are practical estimates based on the code path, the universe size, and the fact that yfinance plus Supabase are network-dependent.

| Step | Estimated Time | CPU intensive? | I/O intensive? | Network dependent? | Memory intensive? | Likely Bottleneck | Optimization Potential |
|---|---:|---|---|---|---|---|---|
| Dashboard auth bootstrap (`/api/status`) | 0.3-2.0 s | Low | Medium | Yes | Low | Firebase verification + Supabase lookup | Medium |
| `fetchWithAuth()` token acquisition | 50-300 ms | Low | Low | Yes | Low | Identity provider round-trip | Low |
| Duplicate-scan check (`user_scans`) | 100-600 ms | Low | Medium | Yes | Low | Supabase query latency | Low-medium |
| `run_scanner()` setup and loop startup | 10-50 ms | Low | Low | No | Low | Negligible | Low |
| Per-ticker yfinance download | 0.2-1.5 s each | Low | High | Yes | Low | External market-data fetch | Very high |
| Full universe download pass | 2-12 min for hundreds of tickers | Low | Very high | Yes | Low | Sequential external requests | Very high |
| Per-ticker feature engineering | 5-30 ms each | Medium | Low | No | Medium | Rolling pandas operations | High |
| Full universe feature engineering | 2-15 s | Medium | Low | No | Medium | Repeated DataFrame work | High |
| Per-ticker prediction | 1-5 ms each | Low | Low | No | Low | Not a bottleneck | Low |
| Full universe prediction | <1-3 s | Low | Low | No | Low | Minor Python loop overhead | Medium |
| Supabase writes for signals | 50-300 ms per write | Low | Medium | Yes | Low | Many small network writes | High |
| `user_scans` write | 100-500 ms | Low | Medium | Yes | Low | Database round-trip | Low-medium |
| Browser rendering after response | 50-300 ms | Low | Low | No | Low | Front-end DOM rendering | Low |

### Interpretation

The scan is dominated by sequential network calls to yfinance, not by XGBoost prediction. Even if model inference were free, the request would still be slow because the app fetches data for every ticker on demand.

## 3) Common inefficiency checklist

| Item | Yes / No | Why |
|---|---|---|
| Reloads the XGBoost model every request | No | `MODEL` is loaded once at module import time in [stock_dashboard/app.py](stock_dashboard/app.py), not inside the route. |
| Reloads the scaler every request | No | `SCALER` is also loaded once at startup. |
| Reloads `feature_list.csv` every request | No | `FEATURE_COLS` is loaded once at startup and reused. |
| Downloads historical data from yfinance every request | Yes | `run_scanner()` downloads 6 months of data for every ticker on each scan. |
| Downloads the same data multiple times | Yes | Each scan re-downloads the same tickers; within a ticker, NSE fallback can trigger a second download to BSE. |
| Calculates indicators from scratch every run | Yes | `compute_features()` recomputes all rolling indicators per ticker on every scan. |
| Calculates features sequentially instead of parallel | Yes | The ticker loop is strictly sequential. |
| Predicts one stock at a time instead of batch prediction | Yes | `MODEL.predict_proba()` is called on one row per ticker in the loop. |
| Makes unnecessary Supabase writes | Yes | Each winning signal is written individually to `trades` and `scan_results`; this is chatty and could be batched. |
| Makes unnecessary Firebase requests | No | Firebase auth verification is required for protected requests. The issue is not excess auth calls, but the fact that auth sits in front of a slow scan. |
| Performs synchronous API calls that could be parallel | Yes | On dashboard bootstrap, history, active trades, last scan, and can-scan checks are awaited sequentially. |
| Recalculates old indicators that could be cached | Yes | Historical bars and their derived indicators are recomputed on every run. |
| Reads large CSV files repeatedly | No | Model, scaler, and feature list are not re-read per request in the inference path. |
| Performs duplicate computations | Yes | The same technical indicators are recomputed per ticker, and the scan is repeated from scratch on every click. |
| Has unnecessary loops | Yes | There is a Python loop over all tickers and another loop over signal writes. |
| Has expensive pandas operations | Yes | Rolling windows, copies, and per-ticker DataFrame transforms are heavy relative to inference. |
| Has unnecessary DataFrame copies | Yes | `compute_features()` starts with `df.copy()`, which is repeated for every ticker. |
| Uses inefficient merge/join operations | No | Not in the inference path. The training pipeline has merges, but the website scan path does not. |
| Uses apply() where vectorization is possible | No | No `.apply()` hotspot appears in the scan path. |
| Uses Python loops instead of NumPy | Yes | The outer scan loop is Python-based and each ticker is handled one by one. |

## 4) Caching opportunities

| What can be cached | Where to cache it | Expected gain |
|---|---|---|
| XGBoost model | In-process global, already done | No further gain; already optimal for this part |
| Scaler | In-process global, already done | No further gain; already optimal for this part |
| Feature list | In-process global, already done | No further gain; already optimal for this part |
| Universe tickers | In-process or small local file cache | Small gain, mostly startup cleanliness |
| Raw yfinance OHLCV data | Disk cache, Redis, or daily parquet store | Very high; likely the largest speedup available |
| Latest feature vectors / last rows per ticker | Redis, Supabase table, or local parquet | Very high; avoids recomputing indicators on every click |
| Daily predictions | Supabase table or Redis keyed by date + model version | Very high for a dashboard, because all users can reuse the same output |
| Dashboard status payload | Short TTL cache in memory or Redis | Medium; reduces repeated `/api/status` lookups |
| `history`, `active_trades`, `last_scan` payloads | Short TTL cache per user/session | Medium; improves page-load responsiveness |
| `can_scan` decision | Short TTL cache or derive from cached scan state | Low-medium |
| Supabase lookups for approved users | Short TTL cache | Low-medium |

### Most valuable cache target

The best cache target is the daily scan result set. If the app precomputes the scan once per morning, the website can read results instantly and avoid the slowest part of the pipeline entirely.

## 5) Parallelization opportunities

### Safe parallel work

- Downloading ticker data
- Computing per-ticker indicators and feature rows
- Writing per-signal rows to Supabase
- Dashboard bootstrap requests that are independent of each other

### Best concurrency primitive

#### ThreadPoolExecutor
Best fit for the current stack.

Why:
- yfinance downloads are network-bound and blocking
- Supabase writes are network-bound and blocking
- the current code already uses blocking libraries, so threads let you overlap wait time without rewriting the stack

#### ProcessPoolExecutor
Use only if feature engineering becomes materially CPU-bound after downloads are cached.

Why not first:
- process startup and serialization overhead are significant
- the current bottleneck is network I/O, not CPU

#### asyncio
Not the best fit for the current codebase.

Why:
- yfinance is not async-native in this code path
- pandas feature engineering is synchronous
- using asyncio would require a larger architectural change than the current code appears to justify

### Parallelization priority order

1. Parallelize ticker downloads
2. Parallelize per-ticker feature engineering if needed after downloads are cached
3. Batch Supabase writes instead of inserting one row at a time
4. Parallelize dashboard bootstrap API calls

## 6) Production architecture review

### Option A: Run everything only when the user presses Run Model

Pros:
- Fresh at request time
- Easy to reason about
- Useful if the scan must reflect live intraday conditions

Cons:
- Slow user experience
- Repeats the same expensive work for every user
- Heavy dependence on yfinance availability at click time
- Harder to scale as user count grows
- Serial execution makes latency unpredictable

### Option B: Run the model automatically once every morning, store predictions, and let the website fetch results

Pros:
- Fastest user experience by far
- One computation serves all users
- Lower yfinance and Supabase load
- Easier to cache and monitor
- Better failure isolation; if the morning job fails, the app can still serve the last successful run

Cons:
- Results can be stale during the day
- Threshold changes may require either cached probability storage or a lightweight re-filtering step
- Requires a scheduler and a small batch-job workflow

### Recommendation

Option B is the better production architecture for this app.

The model is already framed as a daily stock-selection system, not a true intraday execution engine. That makes morning batch computation the correct default. The website should fetch precomputed predictions, then optionally filter by threshold on the server or client side. If you need a manual refresh button, it should be a privileged or debug-only path, not the normal user path.

## 7) Profiling plan

I did not modify code yet, so no `perf_counter()` instrumentation is present in the repository. The right next step is to add timers around the major boundaries below without changing business logic.

### Where to measure

1. Authentication check in `require_auth`
2. Dashboard bootstrap `/api/status`
3. Duplicate-scan check in `/api/scan`
4. `run_scanner()` total duration
5. Per-ticker download duration
6. Per-ticker feature-engineering duration
7. Per-ticker prediction duration
8. Supabase write duration
9. JSON serialization and response return
10. Optional front-end render timing after fetch resolves

### Target output shape

```text
Authentication .......... 0.12 s
Status check ............ 0.31 s
Scan gate ............... 0.08 s
Download data ........... 18.73 s
Feature engineering ..... 24.85 s
Prediction .............. 0.18 s
Supabase upload ......... 2.63 s
Total ................... 46.91 s
```

### What the timers are expected to show

- Authentication should be small relative to the scan
- yfinance downloads should dominate total latency
- feature engineering should be the second-largest block if the universe is large
- prediction should be negligible
- Supabase writes should be visible but not dominant unless many signals are generated

## 8) Optimization opportunities ranked by impact

| Rank | Optimization | Expected speedup | Impact |
|---|---|---:|---|
| 1 | Precompute morning predictions and serve cached results | 10x to 100x | Extremely high |
| 2 | Cache raw market data and re-use daily bars | 5x to 20x | Extremely high |
| 3 | Parallelize yfinance downloads with ThreadPoolExecutor | 2x to 8x | High |
| 4 | Batch Supabase writes | 1.2x to 3x | Medium-high |
| 5 | Cache last-row feature vectors / daily feature snapshots | 2x to 10x | High |
| 6 | Vectorize or simplify per-ticker feature calculation after caching data | 1.2x to 3x | Medium |
| 7 | Parallelize dashboard bootstrap requests | Better perceived latency, 1.1x to 2x on page load | Medium |
| 8 | Reduce duplicate NSE/BSE fallback downloads with a persistent ticker-source map | 1.1x to 2x | Medium |
| 9 | Serve scan results from a precomputed table keyed by date and model version | 10x+ on repeat requests | Extremely high |
| 10 | Add short TTL cache for status and scan metadata | Small to medium | Medium |

## 9) Recommended order of implementation

1. Add profiling timers first so you can measure the baseline precisely.
2. Move scan output generation to a morning batch job and store results.
3. Cache raw market data and derived daily features.
4. Parallelize ticker downloads with threads.
5. Batch database writes.
6. Add short TTL caches for status and dashboard metadata.
7. Only then revisit feature-engineering micro-optimizations.

## Conclusion

The current inference pipeline is functionally correct but not architected for low-latency user interaction. The major issue is that the website still performs the expensive scan work on demand, and that work is mostly network-bound and sequential. The model itself is not the bottleneck. The fastest path to a better user experience is to precompute daily predictions, cache market data and features, and keep the website on a read-mostly path.
