# Empirical methodology notes

The library exposes choices rather than presenting empirical conventions as
universal rules. This document records the reasoning behind the defaults and
the circumstances in which a researcher might choose differently.

## Information timing and look-ahead bias

A portfolio return for month t must use information available before that
return is realized. Monthly characteristics therefore generally need a lag.
Value-weighted returns use beginning-of-period market capitalization, proxied
by the preceding observation. Generic shifts do not verify monthly calendar
adjacency; callers must check gaps or align an explicit calendar. The stock-
momentum implementation separately checks this alignment.

Annual accounting data need an availability rule, not merely `shift(1)`. The
Fama–French convenience constructor follows the reference replication: fiscal-
year t accounting information is used in formation year t+1, portfolios form
in June, and assignments apply from July through the following June. A project
with actual filing dates should use those point-in-time dates. Restated annual
accounts are not historical vintages merely because a June lag is applied.

## Breakpoints and portfolio weights

NYSE breakpoints prevent the numerous small NASDAQ and AMEX firms from
dominating US quantile thresholds. Full-universe and custom breakpoints remain
available because the correct reference universe depends on the research
question and market.

Independent sorts make each assignment from unconditional breakpoints.
This describes breakpoint construction, not statistical independence.
Sequential sorts calculate later breakpoints within earlier portfolios. These
designs answer different questions and should not be interchanged silently.

EW/VW aggregation excludes missing realized returns and renormalizes over
observed securities. That retrospective missingness is not information known
when choosing implementable weights. Formation eligibility must be specified
separately from realized-return availability.

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
Zero alpha is a mean–variance pricing restriction under unconstrained trading
with a risk-free asset; exact return replication additionally requires zero
residual variance. Failure to reject does not prove either restriction.

The regressions select complete observations by asset/specification unless the
caller first imposes a common sample. Notebooks 03–04 impose common samples
within benchmark comparisons; Notebook 05's multifactor fits select their own
complete samples. Their FF3 definitions also differ: 03–04 retain the internal
FF5-derived SMB, whereas 05 uses separately prepared conventional FF3 factors.
Exact input definitions and sample conventions belong in the
[data guide](../data/README.md).

## Time-series spanning and Fama--MacBeth regressions

A time-series spanning regression asks whether a candidate return has an alpha
relative to contemporaneous benchmark-factor returns. A Fama--MacBeth
regression asks whether exposures explain the cross section of returns. The
minimal implementation first estimates fixed full-sample betas when requested,
then runs one cross-sectional regression per period and averages the resulting
risk-premium estimates. HAC inference is applied to those coefficient time
series. It does not include a Shanken errors-in-variables correction, which
should be stated when estimated betas are used as regressors.

## Momentum windows

At month t, momentum signals must exclude the month-t return. A skip period can
also omit the immediately preceding month, as is standard in many stock-
momentum implementations. Holding periods above one create overlapping
vintages, which should be combined explicitly and generally imply serially
correlated strategy returns.

The stock-momentum notebook uses the conventional 12--2 signal: eleven returns
from months t-12 through t-2, followed by a one-month holding period. Signals
are missing when this history is incomplete or contains a calendar gap. The
time-series factor-momentum portfolio divides by the number of factors with a
valid signal and current return in each month; missing returns are excluded
rather than silently replaced with zero. Its cross-sectional counterpart puts
half of gross exposure in above-median factors and half in below-median factors.
In the API, `skip` is the lag of the last included return: stock 12–2 uses
`lookback=11, skip=2`; trailing factor momentum uses `lookback=12, skip=1`.
The factor routines shift observations and require a consecutive calendar
for these labels to refer to calendar months.

## Volatility-managed returns

Current-month realized variance is unknown at the start of the month. Managed
month-t returns therefore use a lagged realized measure. Ex-post constants that
match managed and unmanaged full-sample volatility facilitate Sharpe and alpha
comparisons, but they are not implementable real-time targets. A live strategy
requires a constant estimated only from information available at the time.
The prepared companion constants use an April-2015 estimation cutoff; the
notebook figures separately match volatility over their plotted samples.
Positive exposure weights need not average to the own-factor OLS loading:
that coefficient measures return covariance and depends on normalization.
