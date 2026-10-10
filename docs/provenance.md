# Provenance and validation scope

The library separates reusable calculations from complete empirical projects:

- [Fama–French five-factor replication](https://github.com/jacobkorsgaard/fama-french-five-factor-replication):
  CRSP/Compustat preparation, June formation, portfolio/factor construction,
  and comparison with French benchmarks.
- [Volatility-managed factor portfolios](https://github.com/jacobkorsgaard/volatility-managed-factors-and-momentum):
  the remote recorded by the local `volatility-management-and-liquidity`
  repository; public factor-file preparation, volatility timing, and its
  complete empirical applications. Anonymous GitHub API access confirmed both
  companion repositories are public on 10 October 2026.

Local companion code establishes implementation lineage, not the historical
commit that produced every prepared dataset. Exact known input schemas,
source vintages, and missing provenance are recorded in the
[data guide](../data/README.md#verified-vintage-and-provenance-limits).

## Preserved conventions

The Fama–French implementation compounds ordinary/delisting returns, uses
absolute prices for market equity, applies the preferred-stock hierarchy,
excludes nonpositive book equity, aligns prior-year accounts and prior-December
market equity with June formation, and carries labels July–June. NYSE quantiles
use lower interpolation and ties enter the lower group. Monthly VW aggregation
uses lagged market equity; characteristic factors equally average the required
size cells and FF5 SMB averages three family size components. OP requires
revenue and COGS with missing SG&A/interest treated as zero. These are the
library/companion conventions, not a claim of exact equivalence to every French
historical definition or data vintage.

Volatility management aggregates demeaned daily squared returns and uses
lagged variance. The library's optional normalization matches volatility over
the supplied complete sample; the companion prepared constants use its
April-2015 cutoff, while notebook figures additionally rescale over plotted
samples. These constants have distinct estimation windows and are ex-post
within those windows. Library factor momentum uses the sign of a trailing
**compounded return**, not an arithmetic mean. This educational application
should not be assumed to reproduce every companion strategy definition.

## Reusable interfaces and empirical applications

The package generalizes column names, breakpoint universes, portfolio counts,
conditioning, EW/VW choices, formation timing, momentum horizons, and return
panels. Generalized options are tested, but no claim is made that every option
independently reproduces a companion project's results. Generic row-based lags
require caller-managed calendar alignment; the stock-momentum implementation
adds explicit calendar checks. Missing-return handling is a calculation
convention, not a real-time information rule. See the
[code guide](code-guide.md#formation-breakpoints-and-weights).

All five educational notebooks now exist and use the package where applicable;
Notebook 01 is conceptual. Notebook 02 demonstrates factor spanning, 03 joint
model evaluation, 04 momentum, and 05 volatility management. They consume
prepared inputs instead of duplicating complete source-data pipelines.

The mathematical corrections have focused regression coverage. Notebooks
03–05 were re-executed against unchanged prepared files, their outputs were
compared with the original baseline, and saved results were aligned with the
corrected implementation. The [validation record](empirical-validation.md)
contains numerical comparisons, samples, and checksums. Later educational
Markdown edits preserved executable cells and outputs. This is validation of
the recorded applications, not a general certification of all research designs
or point-in-time data availability.

Documentation validation on 10 October 2026 used a clean editable installation
with Python 3.13, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1, statsmodels 0.15.0,
Matplotlib 3.11.2, and PyArrow 26.0.0. The synthetic workflow and all 52 tests
passed; all five prepared Parquet files were readable. Notebook 03 also
executed successfully with the documented kernel override, writing only to a
temporary directory. Final release review removed the 14 pandas grouping
future-compatibility warnings by using a scalar key for single-column groups.
All 52 tests then passed with those warnings treated as errors, and synthetic
portfolio assignments and returns were unchanged. The original and revised
sorting engines also produced exactly equal assignments and breakpoints in all
seven sorting-test calls, including annual and conditional sorts. A fresh
installation with both optional extras passed dependency checks; all notebook
code cells, saved outputs, figures, and five prepared-input checksums remained
unchanged. All 31 internal links and 260 MathJax expressions validated.
This environment is a validation record, not a
locked environment for exact historical output reproduction.

The library does not acquire licensed observations, parse vendor exports,
resolve CCM links, certify historical accounting vintages, enforce a complete
CRSP universe, or reproduce every companion table. Broader companion AR/GARCH
experiments remain outside this library's notebook sequence.
