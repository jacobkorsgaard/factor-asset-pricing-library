# Empirical methodology notes

The library exposes choices rather than presenting empirical conventions as
universal rules. This document records the reasoning behind the defaults and
the circumstances in which a researcher might choose differently.

## Information timing and look-ahead bias

A portfolio return for month t must use information available before that
return is realized. Monthly characteristics therefore generally need a lag.
Value-weighted returns use beginning-of-period market capitalization, proxied
by the preceding monthly observation.

Annual accounting data need an availability rule, not merely `shift(1)`. The
Fama–French convenience constructor follows the reference replication: fiscal-
year t accounting information is used in formation year t+1, portfolios form
in June, and assignments apply from July through the following June. A project
with actual filing dates should prefer those point-in-time dates.

## Breakpoints and portfolio weights

NYSE breakpoints prevent the numerous small NASDAQ and AMEX firms from
dominating US quantile thresholds. Full-universe and custom breakpoints remain
available because the correct reference universe depends on the research
question and market.

Independent sorts make each assignment from unconditional breakpoints.
Sequential sorts calculate later breakpoints within earlier portfolios. These
designs answer different questions and should not be interchanged silently.

Fama–French factor returns first value-weight stocks within each cell and then
equal-weight the relevant cell returns. This ensures, for example, that the
small and big high-book-to-market portfolios receive equal weight in HML.

## OLS and Newey–West inference

OLS coefficient estimates remain useful for factor regressions, but monthly
financial returns and strategy residuals can be heteroskedastic and serially
correlated. Conventional iid OLS standard errors may therefore misstate
sampling uncertainty. Newey–West/HAC covariance estimates allow both forms of
dependence while leaving coefficient estimates unchanged.

Twelve lags are a common convention for monthly asset-pricing regressions and
match the companion projects. The choice is not a theorem. It roughly permits
dependence across a year and is often used for comparability with prior work.
Researchers should vary the lag length when the strategy construction,
overlapping holding periods, sample frequency, or economic mechanism implies a
different dependence horizon. In particular, an H-month overlapping strategy
mechanically induces serial dependence that the inference design should cover.

## GRS and individual alpha tests

An alpha t-test asks whether one asset's intercept is zero. The GRS test asks
whether all test-asset alphas are jointly zero, accounting for their residual
covariance and the factors' sample Sharpe ratio. The standard GRS F distribution
relies on stronger iid and normality assumptions than HAC inference. Reporting
HAC alpha t-statistics alongside conventional GRS results makes the distinction
visible rather than treating the two procedures as interchangeable.

## Momentum windows

At month t, momentum signals must exclude the month-t return. A skip period can
also omit the immediately preceding month, as is standard in many stock-
momentum implementations. Holding periods above one create overlapping
vintages, which should be combined explicitly and generally imply serially
correlated strategy returns.

## Volatility-managed returns

Current-month realized variance is unknown at the start of the month. Managed
month-t returns therefore use a lagged realized measure. Ex-post constants that
match managed and unmanaged full-sample volatility facilitate Sharpe and alpha
comparisons, but they are not implementable real-time targets. A live strategy
requires a constant estimated only from information available at the time.

