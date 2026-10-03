# Source code guide

This guide explains how the package is organized, what each public function
does, and how data move through the library. The source remains the definitive
description of exact arguments and return values; this document provides the
map an outside reader needs before opening individual modules.

## Design principles

The package uses long pandas panels for security-level work and wide pandas
frames for panels of portfolio or factor returns. It has no hidden global
configuration. Column names, timing choices, breakpoint universes, and
weighting choices are function arguments.

The intended research sequence is:

1. Construct economically meaningful characteristics.
2. Lag or otherwise align the characteristics with the information set.
3. Assign securities to portfolios using reference-universe breakpoints.
4. Aggregate security returns into EW or VW portfolio returns.
5. Combine portfolio returns into factors or retain them as test assets.
6. Evaluate the factors with time-series tests and portfolio statistics.

## `characteristics.py`

This module implements firm-level variables, not data acquisition or generic
cleaning.

- `adjusted_return` combines CRSP ordinary and delisting returns. Including the
  delisting payoff prevents a disappearing firm from losing its final return.
- `market_equity` uses absolute price because a negative CRSP price is a quote
  flag, not negative firm value.
- `book_equity` applies the preferred-stock hierarchy used in the reference
  replication and removes nonpositive book equity.
- `operating_profitability` calculates revenue less COGS, SG&A, and interest,
  scaled by book equity.
- `investment` calculates annual asset growth using prior-year total assets.
- `book_to_market` divides accounting book equity by positive market equity.
- `fama_french_characteristics` joins these definitions with the annual timing
  rules: fiscal-year t accounting data and December t market equity become
  formation-year t+1 signals, followed by July-to-June holding years.

The convenience constructor expects an already cleaned and linked CRSP–
Compustat-style panel. Link-table resolution and vendor-specific parsing remain
outside the library.

## `sorts.py`

`lag_characteristics` shifts signals within security. It is most useful for
monthly signals. Annual Fama–French variables should instead be created with
their explicit formation-year timing.

`quantile_breakpoints` uses lower interpolation. `assign_portfolios` computes
breakpoints within each date or formation period and assigns integer labels
starting at one. Independent sorts compute every set of breakpoints separately.
Sequential sorts condition later breakpoints on earlier assignments.
Explicit probabilities allow non-equal splits such as 30/40/30, while
`conditional_on` identifies the precise earlier sorts used to form later
breakpoint samples.

`assign_annual_portfolios` selects one formation month, calculates assignments
in that cross-section, and carries them through the following annual holding
period. It returns the assigned panel, formation sample, and a tidy breakpoint
table so timing and classifications remain inspectable.

`portfolio_returns` computes EW or VW returns. VW returns use the preceding
security observation's market equity by default. `sort_portfolios` is a small
convenience wrapper that performs assignment and aggregation together.

## `factors.py`

`long_short_factor` and `quantile_spread` turn portfolio returns into generic
long-short factors and preserve both legs. `fama_french_2x3_factor` implements
equal averaging across the required 2×3 cells rather than weighting cells by
their market capitalizations. `factor_from_assignments` supports EW or VW
security-level construction, and `market_excess_return` builds the market
return less the risk-free rate.

`fama_french_five_factors` is a thin composition layer for an already assigned
panel. It calculates three sets of 2×3 cells, HML, RMW, CMA, the three SMB
components, final SMB, and MKT. It does not form annual portfolios or prepare
CRSP--Compustat data.

## `momentum.py`

`momentum_signal` compounds returns over a completed lookback window. `skip`
controls the gap between that window and the holding month. `stock_momentum`
sorts securities on this signal and averages overlapping holding vintages.

`factor_momentum_positions` takes the sign of each factor's trailing compounded
return and equal-weights only positions with a valid signal and current return.
`factor_momentum` applies those positions to contemporaneous factor returns.
`cross_sectional_momentum_positions` and `cross_sectional_momentum` provide a
dollar-neutral median-split counterpart. `conditional_future_returns` and
`lagged_correlation_matrix` support continuation and lead--lag diagnostics.

## `test_assets.py`

The univariate, bivariate, and multivariate wrappers all call `sorts.py`; there
is no parallel sorting implementation. The module also calculates portfolio-
average characteristics and converts returns to excess returns.

## `asset_pricing_tests.py`

`time_series_regression` estimates one factor model. `factor_regressions`
repeats it across test assets and extracts alpha, betas, inference, R²,
adjusted R², and sample size. `pricing_error_summary` summarizes the resulting
alpha cross-section. `spanning_regression` uses the same estimator when the
dependent return is a candidate factor or strategy.

`estimate_factor_betas`, `fama_macbeth_regression`, and
`two_pass_fama_macbeth` provide the minimal two-pass cross-sectional method.
The implementation uses fixed full-sample betas or supplied fixed exposures
and applies HAC inference to the time series of cross-sectional coefficients.
It deliberately omits rolling betas and Shanken corrections.

`grs_test` implements the conventional finite-sample joint test that all model
alphas are zero. Its F reference distribution assumes iid multivariate-normal
residuals; HAC standard errors in separate regressions do not turn the standard
GRS statistic into a HAC GRS test.

The remaining functions calculate Sharpe ratios and compare the ex-post
maximum Sharpe ratio before and after adding candidate returns.
`performance_summary` reports annualized return and volatility, Sharpe ratio,
the HAC t-statistic of the mean, skewness, maximum drawdown, dates, and sample
size for one return or a return panel.

## `validation.py`

`validate_return_series` aligns one constructed return with one external
benchmark and reports means, mean difference, correlation, HAC alpha and
loading, R², and adjusted R². `validate_factor_returns` applies this comparison
across matching factor columns, while `validate_portfolios` applies it to
arbitrary matching portfolio keys. File-format-specific benchmark readers
remain outside the package.

## `volatility_management.py`

Daily squared returns are aggregated to realized variance. Scaling uses the
lagged realized measure, never the current period's realized variance.
Inverse-variance and inverse-volatility scaling are available. Optional
full-sample normalization matches the managed and unmanaged sample volatility;
this constant is useful for comparisons but is not a real-time volatility
target.

## `mean_variance.py`

This module contains classical unconstrained portfolio algebra: portfolio
moments, 1/N, global minimum variance, the tangency portfolio, and the
analytical efficient frontier. The plot function visualizes the risky frontier
and tangency portfolio but does not add constraints or an optimizer framework.
