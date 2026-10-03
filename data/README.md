# Data

The repository does not distribute empirical datasets. In particular, CRSP,
Compustat, and the CRSP/Compustat linking table are licensed products and must
not be committed to version control.

## Local layout

The notebook examples use two kinds of inputs:

- a locally prepared monthly CRSP--Compustat security panel containing returns,
  market equity, exchange identifiers, accounting characteristics, and annual
  portfolio assignments; and
- benchmark factor and portfolio returns downloaded from Kenneth French's Data
  Library for implementation validation.

Raw licensed files may be stored under `data/raw/` and downloaded benchmark
files under `data/reference/`. Both locations are ignored by Git except for
their placeholder files. Prepared files may instead remain in a separate
replication project; notebook paths should then be configured for that local
environment.

Notebooks 2--5 recognize the following environment variables:

| Variable | Prepared input |
|---|---|
| `FAP_FF5_DATA_DIR` | Directory containing internal FF5 factors and test portfolios |
| `FAP_FF5_FACTOR_DATA` | Internal FF5 factor Parquet file used by the momentum notebook |
| `FAP_CRSP_COMPUSTAT_PANEL` | Prepared monthly security-panel Parquet file |
| `FAP_VOLATILITY_DATA` | Prepared factor and volatility-management Parquet file |

When these variables are absent, the notebooks retain the author's sibling-
repository locations as local fallbacks. This keeps the public library free of
licensed observations while making the required paths explicit.

## Minimum panel fields

The exact requirements depend on the method being used. The central sorting
workflow expects:

| Purpose | Typical column |
|---|---|
| Security identifier | `permno` or `id` |
| Month | `date` or `mdate` |
| Adjusted security return | `ret` |
| Market equity used for weights | `market_equity` |
| Breakpoint universe | `exchange` or a Boolean reference indicator |
| Sorting signals | for example `book_to_market`, `profitability`, `investment`, or past return |
| Risk-free return, when needed | `rf` |

Column names are configurable in the public functions. Accounting variables
must be available at formation time, and value weights must use lagged market
equity. The library provides the empirical methods but deliberately leaves
vendor downloads, identifier linking, and project-specific cleaning outside
its scope.
