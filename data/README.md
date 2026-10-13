# Empirical data guide

The notebooks use prepared Parquet files from two companion projects:

- [Fama–French five-factor replication](https://github.com/jacobkorsgaard/fama-french-five-factor-replication): linked firm records, characteristic portfolios, and internal factor returns.
- [Volatility-managed factors and momentum](https://github.com/jacobkorsgaard/volatility-managed-factors-and-momentum): public-source factor returns, momentum, and managed-factor payoffs.

These inputs are obtained or built separately. CRSP and Compustat inputs are
licensed or derived from licensed data. The library does not download them.
A similarly named official factor CSV is not a replacement for a prepared file.

## Required files

| File | Used in | Contents |
|---|---|---|
| `crsp_compustat_monthly_panel_1950_2024.parquet` | 01, 02, 08 | Linked monthly security returns, prices, shares, exchange codes, identifiers, and annual accounting fields. |
| `ff5_factors_internal.parquet` | 02–08 | Monthly `mdate`, `MKT`, `SMB`, `HML`, `RMW`, `CMA`, and `RF`. |
| `ff5_test_portfolios.parquet` | 02, 05, 07, 08 | Monthly 5×5 portfolio returns with `mdate`, `family`, `row_portfolio`, `column_portfolio`, and `ret`. |
| `ff_2x4x4_test_portfolios.parquet` | 07 | Monthly portfolio returns with `mdate`, `family`, `size_portfolio`, `characteristic_1_portfolio`, `characteristic_2_portfolio`, and `ret`. |
| `managed_factors.parquet` | 08, 09 | Official momentum, unmanaged factor returns, lagged realized variance, weights, and managed payoffs. |

Not every notebook reads every field. Its setup cells specify the exact columns
and selected sample. Some prepared files contain additional fields.

## Configure paths

Set these environment variables before starting the notebook kernel. Use
absolute paths to your own prepared files.

```bash
export FAP_FF5_DATA_DIR=/absolute/path/to/ff-prepared
export FAP_CRSP_COMPUSTAT_PANEL="$FAP_FF5_DATA_DIR/crsp_compustat_monthly_panel_1950_2024.parquet"
export FAP_FF5_FACTOR_DATA="$FAP_FF5_DATA_DIR/ff5_factors_internal.parquet"
export FAP_VOLATILITY_DATA=/absolute/path/to/managed_factors.parquet
```

| Variable | Used in | Points to |
|---|---|---|
| `FAP_FF5_DATA_DIR` | 02–07 | Directory containing the internal factor and test-portfolio files. |
| `FAP_CRSP_COMPUSTAT_PANEL` | 01, 02, 08 | Linked firm-panel file. |
| `FAP_FF5_FACTOR_DATA` | 08 | Internal factor file, configured independently of the directory variable. |
| `FAP_VOLATILITY_DATA` | 08, 09 | Managed-factor file. |

Without overrides, the setup cells use sibling-project paths under
`01_complete/fama-french-five-factor-replication` and
`01_complete/volatility-management-and-liquidity`. Check those cells if your
folder layout differs.

## Units and dates

Prepared returns, including RF, are monthly simple decimals: `0.01` means 1%.
Portfolio `ret` is a total return. MKT is an excess return, and characteristic
factors are long–short payoffs. Missing observations remain missing.

The Fama–French files use month-start `mdate` timestamps. The managed-factor file
uses month-end `date` timestamps. Notebook 08 aligns these conventions before
joining sources. Keys must be unique within each security or portfolio series.

In the linked panel, prices are dollars, shares are thousands, and accounting
amounts are millions of dollars. Notebooks 01–02 require the accounting fields
listed in their setup cells, including company identifiers and fiscal dates.

## Definitions and availability limits

The internal SMB is FF5-derived. Three-factor subsets of that file therefore
use a different SMB definition from conventional FF3. Notebook 09 instead uses
separately prepared benchmark columns, as stated in its application.

The June-2020 examples recover annual records from the already lagged panel.
Fiscal-2019 fields appear in July-2020 rows. That row date is not an accounting
publication date. The retained profitability rule requires revenue and COGS
and treats missing SG&A and interest as zero, differing from French's published
expense-availability rule. The notebooks explain these conventions.

The managed-factor file supplies `mom`, unmanaged factors, and fields named
`rv_<factor>_lag1`, `weight_<factor>`, and `managed_<factor>`. Notebook 09 uses
separate `ff5_` market, size, and value columns for FF5 controls. The stored
variance is a sum of squared demeaned daily decimal returns. Prepared scaling
constants use an April-2015 cutoff, while comparison figures additionally match
volatility over their displayed samples. Those normalizations are retrospective.

The saved internal return histories end in December 2024. The managed panel
inspected on 10 October 2026 extends through July 2026. Each application reports
its actual usable dates. Replacing a file or extending its history changes the
empirical analysis.

Original extraction dates, historical accounting vintages, filing availability,
and exact dataset-build commits are not fully established. The examples are
historical analyses of the prepared snapshots, rather than certified
point-in-time backtests.
