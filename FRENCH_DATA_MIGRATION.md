# French-data migration record

Working notes for the later README work; neither README is replaced here.

## Sources and reproduction

Official catalog: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

All URLs below use `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/` followed by the filename. Files belong in `data/raw/french/`. Original CSVs take precedence over ZIPs and are never rewritten. The loader accepts the original filenames; it deliberately rejects the local RTF file called `FF5 Download - 1963_07-2024_12.csv` as a substitute for an original French file.

| Original filename | Required returns | Uses |
| --- | --- | --- |
| F-F_Research_Data_5_Factors_2x3_CSV.zip | Mkt-RF, SMB, HML, RMW, CMA, RF | 04–09 |
| F-F_Research_Data_Factors_CSV.zip | Mkt-RF, SMB, HML, RF | 08 RF history; 09 conventional FF3 |
| F-F_Momentum_Factor_CSV.zip | Mom | 08 validation; 09 momentum |
| F-F_Research_Data_5_Factors_2x3_daily_CSV.zip | Daily five factors, RF | 09 variance |
| F-F_Research_Data_Factors_daily_CSV.zip | Daily three factors, RF | 09 variance |
| F-F_Momentum_Factor_daily_CSV.zip | Daily Mom | 09 variance |
| 25_Portfolios_5x5.csv | 25 value-weighted monthly size/BM total returns | 05, 07 |
| 25_Portfolios_ME_OP_5x5.csv | 25 size/OP total returns | 07 |
| 25_Portfolios_ME_INV_5x5.csv | 25 size/INV total returns | 07 |
| 32_Portfolios_ME_BEME_OP_2x4x4.csv | 32 size/BM/OP total returns | 07 |
| 32_Portfolios_ME_BEME_INV_2x4x4.csv | 32 size/BM/INV total returns | 07 |
| 32_Portfolios_ME_OP_INV_2x4x4.csv | 32 size/OP/INV total returns | 07 |
| 10_Portfolios_Prior_12_2_CSV.zip | Ten prior (2–12) return deciles | 08 |
| 6_Portfolios_ME_Prior_12_2_CSV.zip | Six size/prior-return portfolios | 08 UMD construction |

For portfolio CSVs, the download is the same stem plus `_CSV.zip`. `source_url(key, frequency)` gives every exact URL. `load_french` is offline. Missing-file errors include the required URL. To obtain a missing source explicitly:

```python
from factor_asset_pricing.french_data import download_french, load_french
from pathlib import Path
raw = Path('data/raw/french')
download_french('ff5', raw)  # reuses an existing original; never overwrites it
factors = load_french('ff5', raw)
# For 09: download_french('ff5', raw, frequency='daily')
```

No additional dependencies, processed caches, or companion repositories are needed for 04–09. Loading attaches the source path, download URL, SHA-256, source header, frequency, and units to DataFrame attributes. Retain the originals and hashes to reproduce a particular vintage; official download URLs update over time. Do not commit source datasets or caches.

## Audit and transformations

The original 04–07 used `ff5_factors_internal.parquet`; 05/07 also used `ff5_test_portfolios.parquet` and 07 `ff_2x4x4_test_portfolios.parquet`, from the companion FF5 replication. Original 08 additionally used the linked CRSP–Compustat monthly panel (`permno`, `mdate`, `ret`, `dlret`, `prc`, `shrout`, `exchcd`) and the companion managed-factor file for official momentum. Original 09 used `managed_factors.parquet` from the volatility-management companion.

The shared ingestion module selects only the monthly value-weighted return table, excluding annual returns, equal weights, portfolio characteristics, and security counts. It maps dates to month starts (daily dates remain trading dates), changes percent to decimal once, removes -99.99/-999 sentinels, validates columns and portfolio rank order, and rejects duplicate, reversed, or gapped monthly dates. Mkt-RF becomes MKT and Mom becomes MOM. RF is subtracted once from total portfolio returns; factors and long–short spreads receive no second subtraction.

Analytical methods remain in existing functions: `factor_regressions` (04/07/08), `two_pass_fama_macbeth` (05), mean–variance routines (06), `grs_test`/`maximum_sharpe_ratio`/pricing summaries (07/08), momentum signals and factor-momentum routines (08), and `aggregate_realized_variance`/`volatility_managed_return`/spanning regressions (09). HAC inference retains 12 monthly lags. Existing analytical APIs are unchanged.

04/06 retain December 2024 but start July 1963, the official FF5 inception, rather than July 1962: 738 months instead of 750. 05 keeps July 1964–December 2024 (726 months). 07 preserves family-specific start restrictions: size/BM and size/OP July 1964; size/INV July 1963; size/BM/OP July 1967; size/BM/INV and size/OP/INV July 1964. Complete cases are selected jointly within each test family. Models called FF3 in 04–08 retain FF5 SMB as a nested three-factor subset; 09 retains separate conventional FF3 and FF5 columns.

08 uses January 1951–December 2024 portfolio histories, with FF5 comparisons starting July 1963 and factor-momentum comparisons requiring a trailing signal window. UMD is constructed with `fama_french_2x3_factor` from the published six portfolios and checked against published Mom (tolerance 0.000151 in decimal returns for source rounding). The ten deciles remain separate test assets. Security-level ranking, eligibility, NYSE breakpoints, delisting adjustments, and lagged market-equity weights cannot be reconstructed from portfolio averages: they require licensed CRSP observations. The current notebook states that limitation. The original security-level sort is therefore no longer claimed as executed. The original size lead–lag objective is retained as an additional application using public size quintiles (`Portfolios_Formed_on_ME_CSV.zip`), with an own/cross covariance decomposition and correlation heatmap. Published formation rules differ from the old monthly security sorts.

09 sums within-month demeaned squared daily factor returns, without dividing by day count. A full monthly calendar precedes the one-month shift, so month t uses variance from t−1. Daily returns estimate variance; monthly payoffs come directly from monthly files. Normalization matches volatility through April 2015, retaining those constants afterward; plots match volatility separately on their displayed samples. The endpoint remains July 2026. RMW/CMA start later than FF3/momentum; the common managed six-factor sample begins August 1963. Weights are uncapped; normalization is ex post and is not a real-time leverage target.

## Comparison with original prepared inputs

Saved original-run comparison artifacts were retained outside the repository. Changes reflect source definitions/universes, the shorter FF5 history, and source vintages; they are not forced to match. French changed its production from CRSP FIZ to CIZ beginning with the January 2025 release, which also changes dividend reinvestment conventions and historical returns. Existing local portfolio originals identify the 202605 CRSP database; factor ZIP vintages can differ.

| Statistic | Previous | Public |
| --- | ---: | ---: |
| 04 HML CAPM alpha, % monthly | 0.2946 | 0.3606 |
| 04 CMA CAPM alpha, % monthly | 0.3066 | 0.3460 |
| 05 intercept, % monthly | 0.8032 | 1.0729 |
| 05 intercept HAC t | 1.811 | 2.481 |
| 05 market exposure price, % monthly | -0.0679 | -0.3078 |
| 06 maximum FF5 monthly Sharpe | 0.3265 | 0.2950 |
| 07 size/OP FF5 GRS p-value | 0.2755 | 0.00892 |

Trimming the old 04 HML sample alone changes alpha to 0.3137%; the further increase to 0.3606% is a source difference on matched dates. For 09, the saved comparison's largest unmanaged-return difference is 0.0008 decimals and largest managed-return difference about 0.000156; the largest benchmark-alpha change is about 0.0000424 percentage points monthly. The daily-variance differences are small but nonzero. 08 is a changed construction universe and portfolio architecture, so direct equality to the old linked-security deciles is inappropriate.

The complete test suite passes: 91 tests, with four existing pandas future warnings in the separate security-characteristics tests.

## Validation and scope

On 16–17 October 2026, all six current notebooks executed in fresh `anaconda-finance` Jupyter kernels. A second execution of all code cells also passed with Parquet readers and network access disabled (27 figures generated after restoring the size lead–lag application), demonstrating independence from companion prepared files. Focused synthetic ingestion tests cover units, sentinels, source preservation, ZIP reading, frequencies, dates, gaps, required columns, rank order, section selection, and explicit downloads. Notebook assertions and coverage tables check the empirical samples and missing observations.

The workspace already contained changes to README.md, notebooks 00–03, and unrelated analytical documentation when this recovery resumed. Those existing changes were left untouched. `data/README.md` was already absent and remains absent. No raw datasets, licensed data, or generated caches have been added to version control. Execution requires the original French files locally; obtaining absent originals requires internet access once.
