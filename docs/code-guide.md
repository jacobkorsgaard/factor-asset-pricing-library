# Practical code guide

Install the package as described in the [README](../README.md#installation).
Import functions from `factor_asset_pricing.<module>`; there is no global data
configuration. The library accepts pandas objects and supplies calculations,
not downloads, identifier linking, or a complete empirical replication.

## Workflow and input contract

Prepare eligible securities → align available signals → assign portfolios →
aggregate returns → construct factors or retain test assets → evaluate returns.

| Input | Required structure and conventions |
|---|---|
| Security panel | Long DataFrame with one row per security/month and a unique row index. Defaults: `id`, `date`, `ret`; add characteristic columns, `exchange` for NYSE breakpoints, and `market_equity` for VW returns. Column-name arguments permit alternatives. |
| Dates | pandas timestamps, sorted chronologically within security. Use one consistent month-start or month-end convention; normalize before joining sources. Duplicate security/month rows must be resolved upstream. |
| Returns | Simple decimal returns: `0.01` means 1%. Convert French percent files before use. Distinguish raw long-only returns from excess or self-financing returns. Missing observations stay missing, not zero. Supply finite observed values. |
| Signals and weights | Signals must be available before the holding month's return; market equity is positive and measured in consistent units. Portfolio labels do not imply that signals have been lagged. |
| Regression inputs | Wide DataFrames, assets/factors in columns and unique ordered dates in the index; one dependent return can be a named Series. Supply excess asset returns and excess/self-financing factors. Use distinct column names, avoid `const`, and provide a full-rank design. |
| Risk-free return | One value per date, in the same frequency and units as returns. Subtract it from long-only test assets; do not subtract it again from normalized long–short factors. |

An accounting year or fiscal period-end is not a filing date. Apply actual
availability dates and retain historical statement vintages where needed.
The June accounting lag does not remove restatement or linking look-ahead bias.
See [empirical input requirements](../data/README.md) for the notebook schemas
and the limits of their recorded provenance.

## Formation, breakpoints, and weights

**Monthly sorts:** `assign_portfolios` sorts the supplied signals separately
within each `date_col` (or supplied `formation_col`). `sort_portfolios` combines
assignment and return aggregation; neither function automatically lags signals.
`lag_characteristics` shifts rows within security, producing, for example,
`signal_lag1`. It does not check calendar adjacency. Generic investment,
VW-weight, factor-momentum, and volatility-management lags are likewise
observation based. Reindex to an explicit monthly calendar or check gaps before
using them; do not fill missing returns with zero.

**Annual formation:** `fama_french_characteristics` aligns fiscal-year y−1
accounts and December y−1 market equity with formation year y.
`assign_annual_portfolios` uses June rows by default and carries labels from
July y through June y+1. It returns `panel`, `formation`, and `breakpoints`.
Pass the formation eligibility mask explicitly; annual labels remain fixed
while monthly VW weights update. Merely setting `formation_col` in a monthly
sort does not construct June assignments and carry them forward.

**Breakpoints:** `reference="nyse"` recognizes exchange values `1`, `"N"`, or
`"NYSE"`; `"all"` uses the full supplied universe. A Boolean column name,
index-aligned mask, or callable returning a mask supports custom universes.
Breakpoints use lower interpolation; equality goes to the lower portfolio.
Missing signals or an empty reference sample yield missing assignments. Labels
start at one; ties and distinct breakpoint/investment universes can produce
unequal or empty cells.

`method="independent"` calculates each characteristic's breakpoints separately;
it does not imply statistical independence. `"dependent"`/`"sequential"`
conditions each later sort on all earlier assignments. For BM and OP breakpoints
conditioned on size but not on one another, supply characteristics in the order
`["size", "bm", "op"]` and
`conditional_on={"bm": ["size"], "op": ["size"]}`. Explicit conditioning
replaces the method's default conditioning. Use
`breakpoint_probabilities={"bm": [0.3, 0.7]}` for a 30/40/30 split.

**Returns:** EW averages valid realized returns. VW defaults to the previous
security observation's market equity, excludes nonpositive/nonfinite weights,
and renormalizes over observations with valid labels and realized returns.
Retain prior-period rows when calculating lags; filtering by portfolio first
can incorrectly lag across formation changes. With precomputed beginning-month
weights, pass `lag_weights=False`. Missing realized returns affect the realized
aggregation universe and are not a trading-time eligibility rule. The caller
must decide how unavailable security returns are treated in an implementable
strategy. `stock_momentum` separately checks monthly calendar alignment for
signals, weight lags, and holding vintages.

## Primary API contracts

Arguments below use defaults unless stated. Full signatures and less common
options remain in the linked source docstrings.

| Module / function | Inputs → outputs; important assumptions |
|---|---|
| [characteristics](../src/factor_asset_pricing/characteristics.py): `adjusted_return`, `market_equity`, `book_equity`, `operating_profitability`, `investment`, `book_to_market` | Aligned Series → Series. Delisting and ordinary returns compound; book equity must be positive. OP requires revenue and COGS, treats missing SG&A/interest as zero. Investment uses the preceding supplied observation, not a checked fiscal-year interval. |
| `fama_french_characteristics(panel)` | Linked panel with `permno`, `gvkey`, `date`, `fyear`, `datadate`, `ret`, `dlret`, `prc`, `shrout`, `seq`, `txditc`, `pstkrv`, `pstkl`, `pstk`, `revt`, `cogs`, `xsga`, `xint`, `at` → panel including `retadj`, `me`, `bm`, `op`, `inv`, `ffyear`, `has_dec`, `has_june`. Default `market_equity_scale=1000` converts CRSP market equity in thousands to accounting units in millions for BM. It does not resolve links or verify filing availability. |
| [sorts](../src/factor_asset_pricing/sorts.py): `assign_portfolios(data, characteristics, n_portfolios)` | Long panel → copy with `<characteristic>_portfolio` labels. Counts can be one integer or one per characteristic; explicit probability mappings can replace counts. |
| `assign_annual_portfolios(data, characteristics, n_portfolios)` | Monthly panel → dict of assigned `panel`, June `formation`, and tidy `breakpoints`; requires unique security/formation-year rows. `eligible` accepts Boolean columns, a mask, or callable. |
| `portfolio_returns(data, portfolio_cols)` / `sort_portfolios(...)` | Assigned panel → tidy `date`, label columns, `ret`, `n_firms`; the combined wrapper returns `(returns, assigned_panel)` in that order. |
| [factors](../src/factor_asset_pricing/factors.py): `quantile_spread(portfolio_data, portfolio_col=..., n_portfolios=..., name=...)` | Tidy cell returns → `date`, `<name>_long`, `<name>_short`, `<name>`. Highest label minus label 1; specify count to avoid mistaking an absent top cell for the top quantile. `long_short_factor` accepts explicit `high`/`low` labels and averages available cells within each leg. |
| `fama_french_2x3_factor(cells, size_col=..., characteristic_col=...)` | Six cell returns → characteristic and SMB returns plus legs. Required cells must be present; cell averaging is equal, even when stocks within cells are VW. |
| `fama_french_five_factors(assigned_panel)` | Already assigned panel with `size_portfolio`, `bm_portfolio`, `op_portfolio`, `inv_portfolio`, `ret`, `rf`, `date`, `id`, `market_equity` → dict `factors`, `cells`, `components`. Numeric investment labels 1/2/3 mean conservative/middle/aggressive. MKT uses the supplied universe; final SMB averages three family components. This function does not form portfolios or impose replication eligibility; its single size-label column does not recreate separate family-specific breakpoint universes. |
| [test_assets](../src/factor_asset_pricing/test_assets.py): `characteristic_portfolios` | Sorting wrapper returning `(returns, assignments)`; univariate/bivariate/multivariate wrappers use the same engine. `to_excess_returns` subtracts date-aligned RF from selected return columns. |
| [asset_pricing_tests](../src/factor_asset_pricing/asset_pricing_tests.py): `time_series_regression(asset_returns, factor_returns)` / `spanning_regression(candidate_return, spanning_returns)` | Series + factor DataFrame → fitted statsmodels result (`params`, `bse`, `tvalues`, `pvalues`, `nobs`). Defaults are OLS inference for the former and HAC(12) for the latter; request `cov_type="HAC"` explicitly for other regression interfaces. |
| `factor_regressions(asset_returns, factor_returns)` | Wide panels → asset-indexed alpha/SE/t/p-value, R², adjusted R², `nobs`, and `beta_<factor>`/SE/t columns. Each asset selects complete observations separately. Pre-align/drop missing values jointly when comparisons require a common sample. |
| `grs_test(asset_returns, factor_returns)` | Wide panels → dict `statistic`, `pvalue`, `df1`, `df2`, `nobs`. Uses a joint complete sample, full rank, invertible covariances, and T > N + K; conventional iid Gaussian-error inference, not HAC. Covariance normalization is explained in Notebook 03. |
| `pricing_error_summary(results)` / `performance_summary(returns)` | Regression table → Series of alpha magnitudes; return Series/panel → asset-indexed descriptive table with dates/counts. Performance uses arithmetic annualization, sample SD, HAC mean inference, and initial wealth 1 for drawdowns. Supply excess returns for Sharpe calculations; no automatic RF subtraction. |
| [momentum](../src/factor_asset_pricing/momentum.py): `stock_momentum(data, ...)` | Long panel → `(factor, portfolio_returns)`. The notebook's 12–2 rule is `lookback=11, skip=2, holding_period=1`; `skip` is the lag of the last included return. Longer holds average available fixed-label vintages with monthly weights. `momentum_signal(..., dates=...)` validates calendar windows; without dates it shifts observations. |
| `factor_momentum(factor_returns, ...)` | Wide excess/self-financing returns → Series; default preceding 12 observations, no intervening skipped month (`skip=1`). `factor_momentum_positions` returns weights. Valid signals and current returns determine availability; this missing-return exclusion is retrospective. |
| [volatility_management](../src/factor_asset_pricing/volatility_management.py): `aggregate_realized_variance(daily_returns, return_cols=...)` / `volatility_managed_return(returns, realized_measure)` | Daily decimal returns → tidy `period` (Period dtype) and `rv_<column>` fields. Convert the period key to the monthly return index before scaling. The scaling function expects contemporaneous **variance**, also for `scaling="inverse_volatility"` (it takes the square root), and returns `return`, `lagged_measure`, `weight`, `managed_return`. Default `lag=1`, `normalize=True`; full-sample normalization is ex-post and leverage is uncapped. Do not pass already-lagged variance without accounting for the additional shift. |
| [validation](../src/factor_asset_pricing/validation.py): `validate_return_series`, `validate_factor_returns`, `validate_portfolios` | Date-indexed series/panels, or tidy matching portfolio keys → aligned means, differences, correlation, HAC regression diagnostics and sample coverage. Inputs need matching units and unique keys. No benchmark file reader is supplied. |

`estimate_factor_betas`, `fama_macbeth_regression`, and `two_pass_fama_macbeth`
provide fixed-exposure two-pass estimation with HAC coefficient-series
inference; no rolling betas or Shanken correction is supplied.
[Mean–variance functions](../src/factor_asset_pricing/mean_variance.py) accept
ordered mean vectors and covariance arrays in matching units/frequency and
return weights, moment dictionaries, or a frontier DataFrame. Constraints and
transaction costs are not modeled. `maximum_sharpe_ratio` uses excess returns
and may return unit-gross directions rather than fully invested weights;
`tangency_portfolio` requires a positive-sum direction for a positive-Sharpe,
sum-to-one representation. Zero alpha concerns mean–variance pricing, not
exact monthly return replication.

## Complete synthetic example

Copy this block into `example.py` and run `python example.py` after installing
the core package. It requires no files or notebook dependencies. It illustrates
monthly VW sorts, a high-minus-low factor, excess test assets, HAC alpha tests,
and conventional GRS. The signal is observed at month-end and lagged before
sorting; complete calendars make the generic weight lag a one-month lag.
The synthetic benchmark is an externally generated excess return, so it is not
a linear combination of the test portfolios.

```python
import numpy as np
import pandas as pd

from factor_asset_pricing.sorts import lag_characteristics, sort_portfolios
from factor_asset_pricing.factors import quantile_spread
from factor_asset_pricing.asset_pricing_tests import (
    factor_regressions, grs_test, performance_summary,
    pricing_error_summary, spanning_regression,
)

rng = np.random.default_rng(1729)
dates = pd.date_range("2000-01-01", periods=181, freq="MS")
n_stocks = 60
market = pd.Series(rng.normal(0.005, 0.04, len(dates)), index=dates, name="MKT")
rf = pd.Series(0.0002, index=dates, name="RF")
signal = np.empty((n_stocks, len(dates)))
signal[:, 0] = np.linspace(-1.5, 1.5, n_stocks)
for t in range(1, len(dates)):
    signal[:, t] = 0.98 * signal[:, t - 1] + rng.normal(0, 0.1, n_stocks)
prior_signal = np.column_stack([np.zeros(n_stocks), signal[:, :-1]])
beta = rng.uniform(0.7, 1.3, (n_stocks, 1))
returns = (rf.to_numpy()[None, :] + beta * market.to_numpy()[None, :]
           + 0.003 * prior_signal + rng.normal(0, 0.06, signal.shape))
market_equity = 1000 * np.cumprod(1 + returns, axis=1)
panel = pd.DataFrame({
    "id": np.repeat(np.arange(n_stocks), len(dates)),
    "date": np.tile(dates, n_stocks),
    "exchange": np.repeat(np.where(np.arange(n_stocks) < 40, 1, 3), len(dates)),
    "signal": signal.ravel(), "ret": returns.ravel(),
    "market_equity": market_equity.ravel(),
})
assert not panel.duplicated(["id", "date"]).any()
assert (panel["ret"] > -1).all()

lagged = lag_characteristics(panel, "signal", lags=1)
portfolios, assignments = sort_portfolios(
    lagged, "signal_lag1", n_portfolios=5,
    reference="nyse", weighting="vw", lag_weights=True,
)
factor = quantile_spread(
    portfolios, portfolio_col="signal_lag1_portfolio",
    n_portfolios=5, name="HML_SYNTH",
).set_index("date")["HML_SYNTH"]
raw_assets = portfolios.pivot(
    index="date", columns="signal_lag1_portfolio", values="ret"
).rename(columns=lambda q: f"P{int(q)}")
sample = pd.concat([raw_assets, market, rf, factor], axis=1, sort=True).dropna()
assets = sample[raw_assets.columns].sub(sample["RF"], axis=0)
benchmark = sample[["MKT"]]

fit = spanning_regression(sample["HML_SYNTH"], benchmark, hac_lags=12)
results = factor_regressions(assets, benchmark, cov_type="HAC", hac_lags=12)
joint = grs_test(assets, benchmark)
assert len(sample) == 180 and joint["nobs"] == 180
print("Synthetic factor alpha (decimal monthly):", fit.params["const"])
print("Newey–West alpha t:", fit.tvalues["const"])
print(pricing_error_summary(results))
print("Conventional GRS:", joint)
print(performance_summary(sample["HML_SYNTH"]))
```

The five portfolios and factor share 180 complete months. The first month is
excluded because neither a lagged signal nor a lagged weight is available.
Statistical significance in this designed simulation is not empirical evidence
for an investment strategy. GRS and HAC tests retain their different assumptions.
