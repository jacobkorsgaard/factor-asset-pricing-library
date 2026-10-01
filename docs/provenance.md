# Provenance and alignment

This library collects reusable methods from two companion empirical projects:

- [Fama–French five-factor replication](https://github.com/jacobkorsgaard/fama-french-five-factor-replication)
- [Volatility-managed factors and momentum](https://github.com/jacobkorsgaard/volatility-managed-factors-and-momentum)

The companion repositories remain the complete empirical applications. This
library extracts their reusable calculations and makes selected dimensions and
column names configurable. It does not claim that every generalized interface
has independently reproduced every result in those projects.

## Directly preserved conventions

### Fama–French replication

- Ordinary and delisting returns are compounded when both are present.
- Market equity is absolute price times shares outstanding.
- Preferred stock uses redemption, liquidation, then carrying value.
- Nonpositive book equity is excluded.
- Operating profitability is revenue less COGS, SG&A, and interest, divided by
  book equity; missing SG&A and interest are treated as zero.
- Investment is annual asset growth relative to lagged total assets.
- Fiscal-year t accounting values become formation-year t+1 signals.
- Book-to-market uses prior-December market equity in matching units.
- Fama–French holding years run from July through June.
- NYSE breakpoints use lower interpolation and breakpoint equality enters the
  lower portfolio.
- Monthly VW returns use prior-month market equity.
- A 2×3 characteristic factor equally averages high and low cells across size.
- The associated SMB component equally averages the three small and three big
  characteristic cells.

### Volatility-management project

- Monthly realized variance is the demeaned sum of squared daily returns.
- Managed month-t returns use a lagged realized measure.
- Inverse-variance scaling can be normalized with one positive full-sample
  constant to match unmanaged and managed sample volatility.
- Default factor momentum takes the sign of the preceding 12-month arithmetic
  mean and equal-weights available factor positions.
- Monthly spanning regressions default to Newey–West/HAC inference with 12
  lags in this library's spanning interface.

## Generalizations introduced here

- Quantile sorts accept arbitrary portfolio counts and up to three dimensions.
- Reference breakpoints may use NYSE, the full universe, or a custom mask.
- Sequential sorting conditions each later signal on all earlier assignments.
- Portfolio returns and factors can be EW or VW.
- Momentum exposes configurable lookback, skip, and holding periods.
- Volatility management additionally permits inverse-volatility scaling.
- Regression and mean–variance functions accept arbitrary return panels.

These generalizations should be viewed as transparent extensions of the source
logic, not as results validated in the companion replications.

## Deliberately project-specific work

The library does not acquire licensed data, parse vendor exports, resolve CCM
links, impose a complete CRSP universe, reproduce every project table, or write
project outputs. The Fama–French replication remains the source for the full
June formation and July–June factor-replication pipeline. The volatility
project remains the source for its complete data build, AR and GARCH exercises,
and empirical analysis.

Future notebooks will explain and demonstrate the reusable methods by calling
the package. They will not duplicate the implementation or replace the complete
research projects.

