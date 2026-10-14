# French data migration: audit and validation record

Validated 14 October 2026. This is the working record for later README edits;
the main README was left unchanged and `data/README.md` was deleted without
replacement. Notebooks 00–03 and both companion repositories were left untouched.

## Audit and retained methods

| Notebook | Previous external inputs | Required public inputs and retained calculations |
| --- | --- | --- |
| 04 | `ff5_factors_internal.parquet` from the FF5 replication | Monthly MKT, SMB, HML, RMW, CMA; `factor_regressions`, OLS/HAC alpha comparisons, residual diagnostics and spanning scatterplots. No security observations needed. |
| 05 | Internal factors and `ff5_test_portfolios.parquet` (Size × B/M) | Monthly MKT and RF, 25 value-weighted total returns; subtract RF once; `two_pass_fama_macbeth` with full-sample first-pass betas, unrestricted intercept, 12-lag monthly HAC; retain fitted means and pricing-error plots. The old loader also restricted the sample using complete FF5 observations; the sample dates remain fixed. |
| 06 | Internal factors | Monthly five-factor payoffs; arithmetic means, sample covariance (T−1), correlations; existing GMV, tangency, efficient-frontier and portfolio-statistics functions. Signed unit-sum factor exposures and zero risk-free intercept remain unchanged. |
| 07 | Internal factors, 5×5 portfolios, `ff_2x4x4_test_portfolios.parquet` | Monthly FF5 and RF; six published value-weighted portfolio families. RF subtraction, `factor_regressions`, `grs_test`, `pricing_error_summary`, and `maximum_sharpe_ratio`; common complete samples within families; alpha/loading grids retain their economic order. |
| 08 | Internal factors; CRSP–Compustat monthly panel; momentum from `managed_factors.parquet` | Published monthly FF5, RF, Mom, size quintiles and prior-(2,12) deciles. Retain lead–lag covariance decomposition, P10−P1 WML, UMD spanning, conditional factor returns, 1/3/6/12-month factor momentum, decile pricing/GRS, and bidirectional spanning using existing library functions. |
| 09 | `managed_factors.parquet` from volatility-management repository | Daily and monthly FF3, FF5 and Mom. `aggregate_realized_variance`, `volatility_managed_return`, own-factor/model spanning and Sharpe functions; retain cumulative growth, alpha/loading heatmaps and downside measures. Recession and forecast-model columns in the old wide panel were unused and are not needed. |

Earlier 04–07 loaders used `FAP_FF5_DATA_DIR`; 08 used
`FAP_CRSP_COMPUSTAT_PANEL`, `FAP_FF5_FACTOR_DATA`, and `FAP_VOLATILITY_DATA`;
09 also used `FAP_VOLATILITY_DATA`. All six now load from this repository's
`data/raw/french`, with no companion path or Parquet reads.

**Security-level limitation in 08:** the original panel supplied permno, month,
ret, dlret, price, shares, and exchange. It compounded delisting-adjusted
returns, computed market equity, restricted exchanges to NYSE/AMEX/NASDAQ,
required observed returns and positive equity, then sorted monthly using NYSE
breakpoints and lagged value weights. Momentum used eleven consecutive returns
(t−12 through t−2), skip=2, a one-month holding period, and decile 10 minus 1.
Those stock assignments and alternative overlapping security-level holdings
cannot be reconstructed from public portfolio returns. The construction equation,
timing explanation and library API remain; the notebook explicitly describes the
unavailable CRSP exercise. Published prior-(2,12) deciles preserve its payoff and
pricing objectives. They use the full French universe rather than the linked
universe. French size quintiles are formed each June, replacing monthly size
sorts. WML versus UMD now compares two published portfolio architectures, not an
independent stock-level validation. No licensed data are needed to execute 08.

## Sources and transformations

Official entry point: [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
Every exact download URL, original local filename, SHA-256, source-header vintage,
required output column, frequency, coverage and missing-cell count is recorded in
[french-source-manifest.csv](french-source-manifest.csv). It contains metadata only.

`src/factor_asset_pricing/french_data.py` is the shared loader. It recognizes:

- FF3 and FF5 original monthly and daily CSV/ZIP files, including RF.
- Monthly and daily momentum (`Mom` becomes `MOM`; 08 labels it `UMD`).
- Size quintiles from `Portfolios_Formed_on_ME` and momentum deciles from
  `10_Portfolios_Prior_12_2`.
- `25_Portfolios_5x5`, `25_Portfolios_ME_OP_5x5`, `25_Portfolios_ME_INV_5x5`,
  and the three `32_Portfolios_ME_*_2x4x4` characteristic families.

Local original CSVs (including uppercase `.CSV`) take precedence over local
original ZIPs. An absent source is fetched from its registered Dartmouth HTTPS
URL, validated and saved atomically as the original ZIP; its bytes are preserved.
Malformed local sources raise rather than being silently replaced. Use
`load_french(..., download=False)` for explicit offline ingestion. Factor source
headers, portfolio rank order and required columns are checked before renaming.
Only the contiguous requested return section is read: annual returns, equal
weights, counts and characteristic tables never enter the monthly panels.

Source return percentages are divided by 100; −99.99/−999 become missing before
conversion. Monthly YYYYMM dates become unique, increasing calendar month starts;
missing calendar months raise. Daily YYYYMMDD dates remain observed trading dates,
without filling weekends or compounding them into monthly returns. Portfolio
names become S1C1–S5C5, S/B−1−1 through S/B−4−4, or P1–P10, in verified source
order. These are total portfolio returns; RF is subtracted once in pricing tests.
MKT is excess and long–short factors are self-financing, so RF is not subtracted
again. In 08, FF3 RF covers the full 1951–2024 Winners/Losers Sharpe sample.

04–08 retain FF5 SMB in their nested three-factor comparisons. 09 retains FF3
SMB for the unmanaged/managed SMB strategy and FF3 benchmarks, with separately
published FF5 columns for FF5 benchmarks. These definitions are not interchangeable.

For 09, sum demeaned squared daily returns within each calendar month (min_obs=2),
join variance to the complete monthly calendar, then lag one month. Compute
unscaled f/RV with the library; estimate one positive volatility-matching constant
per factor through April 2015 (sample SD, ddof=1), and apply it to the entire
history. No caps or leverage limits are added. Comparison plots still match
volatility separately on plotted samples. The old forward/backward shifting
construction check remains a proportionality check; actual daily variance is now
independently rebuilt before it. Normalization is ex post, not implementable in
real time before its calibration endpoint.

The six pre-existing portfolio CSVs are May 2026 CRSP vintages and were preserved.
New downloads are August 2026 vintages. The local `FF5 Download - 1963_07-2024_12.csv`
is actually RTF containing transformed decimal returns, not an original French
CSV; it was preserved but deliberately excluded. No intermediate/cache files
were needed in `data/processed`. Its generated contents are now ignored by Git,
as are raw third-party inputs under the existing ignore rule.

## Samples and validation

| Exercise | Previous sample | Public-data sample |
| --- | --- | --- |
| 04 and 06 | July 1962–December 2024, 750 months | July 1963–December 2024, 738 months; published FF5 starts July 1963 |
| 05 | July 1964–December 2024, 726 | Unchanged |
| 07 Size × B/M, OP, B/M × INV, OP × INV | July 1964–December 2024, 726 | Unchanged |
| 07 Size × INV | July 1962–December 2024, 750 | July 1963–December 2024, 738 |
| 07 Size × B/M × OP | July 1967–December 2024, 690 | Unchanged |
| 08 size lead–lag / WML deciles | January 1950 / January 1951–December 2024 | Same date bounds, 900 / 888 months |
| 08 UMD on factors | July 1962–December 2024, 750 | July 1963–December 2024, 738 |
| 08 FMOM/decile pricing/spanning | July 1963–December 2024, 738 | July 1964–December 2024, 726, after 12-month factor-signal warmup |
| 09 | Source-specific histories through July 2026 | Same bounds and April 2015 normalization cutoff; common six-factor sample August 1963–July 2026, 756 months |

All 14 parsed return tables have zero missing return cells after selecting the
required columns. Monthly inputs have no calendar gaps. The full 09 combined
panel intentionally has pre-inception missing columns and initial lagged-variance
missing values; these are not filled with zero. 08's factor-leg comparison drops
months lacking a positive or negative signal group, as before. Notebooks display
coverage, and fixed-sample/calendar/variance/normalization checks guard ingestion
and construction. Daily market-holiday gaps are expected.

Validation: **67 tests passed**, including 15 new synthetic-fixture ingestion
cases for CSV/ZIP, metadata sections, frequencies, dates/gaps/duplicates, units,
sentinels, required columns and rank ordering, size/decile selection, offline
reuse, original-byte preservation, and failed-download handling. All six
notebooks executed in Jupyter with no cell errors and rendered **28 figures**.
They also executed in `/tmp/fap-public-validation`, containing only this library,
its notebooks and local French sources, without either companion repository.
Representative spanning, frontier, pricing and wealth figures were inspected.
Execution used the installed anaconda-finance kernel; no new dependency was added.

Before migration, 04–07 and 09 were executed read-only against the existing
companion inputs and their statistics captured temporarily. 08 comparisons use
its saved pre-migration outputs; the expensive CRSP stock sorts were not rerun.
The earlier figures and new figures retain the same analytical layouts; data
points, fitted lines, frontier slopes, heatmap values and wealth paths are
recomputed. Numerical result commentary was updated to the validation snapshot.

| Selected statistic | Previous | Public |
| --- | ---: | ---: |
| 04 HML CAPM alpha (% monthly) | 0.295 | 0.361 |
| 04 RMW / CMA CAPM alpha (% monthly) | 0.345 / 0.307 | 0.338 / 0.346 |
| 05 market exposure price (% monthly), NW statistic | −0.068, −0.15 | −0.308, −0.67 |
| 05 intercept (% monthly), NW statistic | 0.803, 1.81 | 1.073, 2.48 |
| 06 maximum monthly Sharpe, three-factor / FF5 | 0.173 / 0.327 | 0.182 / 0.295 |
| 07 Size × OP FF5 GRS p-value | 0.276 | 0.0089 |
| 08 size-index lag-one correlation | 0.103 | 0.097 |
| 08 WML mean (% monthly), correlation with UMD | 1.224, 0.899 | 1.193, 0.897 |
| 08 UMD FF5 alpha (% monthly), NW statistic | 0.674, 3.567 | 0.703, 3.661 |
| 08 FMOM FF5 alpha (% monthly), NW statistic | 0.215, 3.460 | 0.235, 3.528 |
| 08 UMD / FMOM augmented-decile mean absolute alpha (% monthly) | 0.124 / 0.128 | 0.124 / 0.124 |
| 09 VM MOM alpha on FF5+MOM (% monthly), NW statistic | 0.879, 5.282 | 0.879, 5.282 |

The changes are not forced to match. 05's intercept now rejects zero at 5%; 07's
FF5 GRS rejects all six families rather than five; 08's added FMOM and UMD have
almost identical mean absolute errors, while UMD still removes more extreme-decile
spread alpha. These changed conclusions are explained in the notebooks.

Sample trimming alone does not explain 04: using July 1963–December 2024 for the
old internal factors gives HML/RMW/CMA alphas 0.314/0.340/0.306%, versus public
0.361/0.338/0.346%. Differences also reflect internal versus published factor and
portfolio universes, construction/eligibility definitions and revised source
vintages. Those effects are not separately identified by this comparison.

09 uses the same methodology and date bounds. On overlapping dates, the largest
monthly underlying return revision is 0.0008 in decimals (0.08 percentage points),
the largest realized-variance revision is 5.714e−5, and the largest managed-return
revision is 0.000156 (0.0156 percentage points). The largest benchmark-alpha change
is 0.0000424 percentage points monthly. Its qualitative conclusions are unchanged.
The full-history MKT wealth plot and common-sample Sharpe table use different
histories; the notebook now explains that distinction explicitly.

## Reproducibility limitations and later documentation

French download URLs supply revisable histories, not frozen releases. The
[official library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
notes the January 2025 switch from CRSP FIZ to CIZ: dividends are reinvested at
ex-dates rather than month-end in the newer compounded-daily monthly returns.
Do not infer that every old internal input used the same legacy convention.
The local source mix also has different monthly vintages; hashes identify the
exact validated originals, but fresh downloads may revise even fixed samples.
Retain/archive the original files locally to reproduce this snapshot. They are
not committed. Current French histories do not establish point-in-time data
availability; transaction costs, financing and real-time normalization remain
outside these educational applications.

Later README work should document: required public files and URLs (manifest),
automatic download/offline behavior and network requirement for absent files,
month-start dates/decimal units and RF handling, nested versus conventional SMB,
fixed samples and FF5 inception, 08's explicit CRSP limitation and annual size
formation, 09's daily-risk timing and April 2015 normalization, source hashes and
vintage mix, and untracked raw/intermediate files. No operational dependency on
licensed or companion data remains in notebooks 04–09.

## Subsequent workflow simplification

Manual source downloads are now the only ingestion workflow. Place original CSV or ZIP files in `data/raw/french/`. `load_french` reads local files and reports the official URL when a file is missing. Automatic downloading and its option were removed. Financial calculations and source parsing conventions are unchanged. Earlier download and execution descriptions above record the initial migration.
