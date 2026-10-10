# Prepared empirical inputs

The synthetic example in the [code guide](../docs/code-guide.md#complete-synthetic-example)
needs no files. Notebooks 02–05 read the five prepared Parquet inputs below;
they do not download data or rebuild companion projects. No empirical datasets
are distributed. CRSP, Compustat, and CCM-linked panels are licensed or derived
from licensed data. French factor source files are public, but their derived
managed panel must still be obtained or built separately.

## Paths and common conventions

Run notebooks from the repository root or `notebooks/`. Set these environment
variables **before starting the kernel** to override the author's sibling-project
fallbacks. Variables name files except for `FAP_FF5_DATA_DIR`, which names a directory.

| Notebooks | Variable | Expected file(s) / default relative to the repository's parent |
|---|---|---|
| 02, 03 | `FAP_FF5_DATA_DIR` | `01_complete/fama-french-five-factor-replication/data/interim/Python/`; contains the three FF files below |
| 04 | `FAP_FF5_FACTOR_DATA` | Same directory's `ff5_factors_internal.parquet`; independent of `FAP_FF5_DATA_DIR` |
| 04 | `FAP_CRSP_COMPUSTAT_PANEL` | Same directory's `crsp_compustat_monthly_panel_1950_2024.parquet` |
| 04, 05 | `FAP_VOLATILITY_DATA` | `01_complete/volatility-management-and-liquidity/data/processed/managed_factors.parquet` |

For example, on macOS/Linux, replace these absolute paths with your own:

```bash
export FAP_FF5_DATA_DIR=/absolute/path/to/ff-prepared
export FAP_FF5_FACTOR_DATA="$FAP_FF5_DATA_DIR/ff5_factors_internal.parquet"
export FAP_CRSP_COMPUSTAT_PANEL="$FAP_FF5_DATA_DIR/crsp_compustat_monthly_panel_1950_2024.parquet"
export FAP_VOLATILITY_DATA=/absolute/path/to/managed_factors.parquet
```

All prepared returns are monthly **simple decimals**, including RF. Portfolio
returns are raw long-only returns; market factors are excess returns and
characteristic/momentum factors are self-financing spreads. French raw CSV
returns are percent and are divided by 100 in the companion parser. Missing
history stays missing. Security-month and date/portfolio keys must be unique.
Do not replace these inputs with similarly named official CSV files.

## Fama–French companion inputs

Produced by the [Fama–French five-factor replication](https://github.com/jacobkorsgaard/fama-french-five-factor-replication).
The local preparation uses CRSP monthly stocks and delistings, Compustat annual
fundamentals, CCM link history, and CRSP Treasury yields from WRDS. The
companion [data instructions](https://github.com/jacobkorsgaard/fama-french-five-factor-replication/blob/main/data/README.md)
record query fields and source filenames. All four prepared inputs below are
derived from licensed data, not public French return downloads.

### `ff5_factors_internal.parquet` — Notebooks 02–04

One row per month, timestamp `mdate` at month start (`YYYY-MM-01`). Required
columns: `MKT`, `SMB`, `HML`, `RMW`, `CMA`, `RF`.

- `MKT`: companion-universe VW delisting-adjusted market return minus RF.
- `HML`, `RMW`, `CMA`: value, profitability, and conservative-investment spreads
  using value-weighted stocks and equal averages of size cells.
- `SMB`: FF5-style average of the B/M, OP, and INV size spreads.
- `RF`: companion Treasury proxy, not an imported French RF column. The pipeline
  converts annualized `TMYTM` percent yield to `exp((TMYTM/100)*(30/365))-1`,
  then averages within month.

The inspected file spans February 1950–December 2024; factor-specific histories
and complete-case samples are shorter. Notebook 02 drops incomplete factor
rows. Notebooks 03–04's label **FF3** selects MKT/SMB/HML from this same file:
it retains FF5-derived SMB, rather than conventional FF3's B/M-only size spread.
The definitions are preserved, not silently benchmark-substituted.

### `ff5_test_portfolios.parquet` — Notebooks 02–03

Tidy monthly table with `mdate`, `family`, `row_portfolio`, `column_portfolio`,
`ret`. The prepared file also has `n_firms` (valid-return count).

`family` is `size_bm`, `size_op`, or `size_inv`. Integer `row_portfolio` is size
1–5 (small to big); `column_portfolio` is the characteristic 1–5 (low to high).
`ret` is the monthly VW, delisting-adjusted raw portfolio return. Both sorts
use independent reference breakpoints. Keys are
`(mdate, family, row_portfolio, column_portfolio)`. The file's overall coverage
is July 1952–December 2024; cells and families can begin later.

### `ff_2x4x4_test_portfolios.parquet` — Notebook 03

Tidy columns: `mdate`, `family`, `size_portfolio`,
`characteristic_1_portfolio`, `characteristic_2_portfolio`, `ret`;
`n_firms` is present in the prepared file. `size_portfolio` uses `"S"`/`"B"`;
characteristic labels are integers 1–4, ascending in the signal.

| `family` | First characteristic | Second characteristic |
|---|---|---|
| `size_bm_op` | Book-to-market | Operating profitability |
| `size_bm_inv` | Book-to-market | Investment |
| `size_op_inv` | Operating profitability | Investment |

Both quartile breakpoint sets are conditioned on size, not sequentially on
one another. `ret` is a raw monthly VW return. Keys combine date, family, and
all three labels. Overall file coverage is July 1960–December 2024.

Notebook 03 pivots each family to wide returns, joins all six factor/RF fields,
and drops any incomplete row **before** fitting all three benchmarks. Thus
models share dates within each family, but families differ. Saved samples end
in December 2024 and begin in July 1964 (size_bm, size_op, size_op_inv), July
1962 (size_inv), July 1964 (size_bm_inv), or July 1967 (size_bm_op). Exact counts
and input checksums are in [empirical validation](../docs/empirical-validation.md#sample-and-definition-checks).

### `crsp_compustat_monthly_panel_1950_2024.parquet` — Notebook 04

Only these columns are read: `permno` (security ID), `mdate` (month-start
timestamp), `ret` (ordinary return), `dlret` (delisting return), `prc` (signed
CRSP price), `shrout` (shares in thousands), and `exchcd` (1/2/3 for
NYSE/AMEX/NASDAQ). Overall coverage is January 1950–December 2024.

The linked panel has additional accounting fields, but Notebook 04 does not
use them as momentum signals. It compounds `ret` with `dlret`, constructs
market equity as `abs(prc)*shrout`, and retains exchanges 1–3, observed adjusted
returns, and positive market equity. This is a CRSP–Compustat-linked universe,
not the full official momentum universe. NYSE deciles use eleven monthly
returns t−12 through t−2 and lagged value weights; holding is one month.
Calendar gaps invalidate signals or weights rather than extending the skipped
month. The saved stock-performance sample is January 1951–December 2024.

## Public-source managed-factor input

### `managed_factors.parquet` — Notebooks 04–05

Prepared by the volatility-management companion project (its local repository
remote redirects to [volatility-managed-factors-and-momentum](https://github.com/jacobkorsgaard/volatility-managed-factors-and-momentum)).
Public source returns come from the [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
The local companion build reads monthly and daily CSV versions of
`F-F_Research_Data_Factors`, `F-F_Research_Data_5_Factors_2x3`, and
`F-F_Momentum_Factor`. Source files and this derived panel are not distributed
here; a prepared copy is sufficient for these notebooks.

One row per month, timestamp `date` at month end (`YYYY-MM-DD`); inspected
coverage is July 1926–July 2026. Required fields:

| Consumer | Columns / definitions |
|---|---|
| 04 | `date`, `mom`: official French Mom/UMD winner-minus-loser return |
| 05 unmanaged factors | `mkt_rf`, `smb`, `hml` from the conventional FF3 source; `rmw`, `cma` from FF5; `mom` from the momentum source |
| 05 FF5 controls | `ff5_mkt_rf`, `ff5_smb`, `ff5_hml`, `rmw`, `cma`; FF5+MOM additionally uses `mom` |
| 05 managed factors | For each `f` in `mkt_rf`, `smb`, `hml`, `rmw`, `cma`, `mom`: `rv_<f>_lag1`, `weight_<f>`, `managed_<f>` |

`rv_<f>_lag1` is the preceding calendar month's demeaned sum of squared daily
decimal returns (squared-return units). `weight_<f>` is dimensionless exposure
`c_f/rv_<f>_lag1`; `managed_<f> = weight_<f> * f`. The companion requires at
least two observed daily returns per variance estimate. Extra AR/GARCH and
recession columns are not required by these library notebooks.

The current companion source sets its normalization cutoff to **30 April
2015**, an endpoint inferred from the original replication's observation
counts. All six stored scale constants were independently checked against this
sample, rather than the full panel through 2026, and match the construction
code. This does not establish an archived build commit for every stored column. The constants are ex-post for their estimation
sample; applying them later does not retroactively make that sample a live
backtest. Notebook 05's figures additionally match volatility on each plotted
comparison sample, using future observations in that sample.

Notebook 04 converts both sources to month-start timestamps before joining.
Its official-UMD regressions share July 1962–December 2024 (750 months);
stock-decile pricing with FMOM shares July 1963–December 2024 (738 months).
Each comparison fixes a complete sample across its benchmark specifications.
Other continuation/horizon summaries use their available histories.

Notebook 05 retains month-end dates. Its six own-factor comparisons share one
complete sample (saved: August 1963–July 2026); multifactor regressions select
complete dates separately for each dependent factor/benchmark combination.
The longer momentum/downside comparison has its own common sample (January
1927–July 2026). A comparison across benchmark alphas can therefore involve
both new controls and changed sample coverage. Its FF3 uses conventional
`mkt_rf/smb/hml`, unlike Notebooks 03–04's nested internal benchmark.

## Verified vintage and provenance limits

Inspection on 10 October 2026 established the schemas and coverage above.
The six local French CSV headers used by the volatility companion all identify
the **202607 CRSP database**. This is a source-database vintage, not a verified
download or build timestamp. The FF companion's documented validation benchmark
is the [December 2024 French archive](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library_202412_archive.html),
which the provider identifies as the legacy FIZ release. That benchmark archive
is not proof of the proprietary WRDS extraction vintage. Prepared-file hashes
record the exact files used for saved validation in
[empirical validation](../docs/empirical-validation.md#prepared-input-checksums).
Current French downloads can differ from these snapshots; extending or replacing
inputs changes the empirical experiment.

Not established: WRDS extraction dates/database releases, original accounting
statement vintages and filing availability, raw-file download timestamps,
and the exact source commit/environment that created each prepared file.
Coverage endpoints and filenames must not be used as substitutes for that
missing provenance. Record these when rebuilding through the companion projects.

The annual convention maps prior-fiscal-year accounts to June formation;
it does not validate publication dates or undo subsequent restatements. The
library/replication OP rule requires revenue, COGS, and positive book equity,
with missing SG&A/interest treated as zero; it differs from French's published
revenue-plus-at-least-one-expense eligibility rule. Historical links, filing
availability, eligibility, and delisting completeness remain preparation
responsibilities. No accounting or benchmark convention has been changed here.
