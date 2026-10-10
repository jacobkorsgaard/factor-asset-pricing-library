# Empirical validation of correctness corrections

Validated 2026-10-10 using the existing `anaconda-finance` kernel and the current working-tree package. Only Notebooks 03–05 were regenerated. The comparison baseline is the original source and notebook code at commit `331c762f521af8c1e626fc26b766bbb59173d3eb`.

Original-code reruns reproduce every previously saved numerical text table in all three notebooks. Full-precision objects captured during both runs were compared with unchanged indexes, columns, sample counts and dates; numerical comparisons used absolute tolerance 1e-12 and relative tolerance 1e-11. The original datasets were read without modification, and their SHA-256 checksums were verified after execution.

## Notebook 03: GRS normalization

All 18 GRS statistics increase and their p-values decrease. All 5% joint-test decisions are unchanged. Portfolio returns, alphas, HAC inference, factor loadings, pricing-error summaries and adjusted R² are unchanged. FF5 still rejects five of six portfolio families; Size × OP remains the exception. The existing formula is now explicitly identified as using divisor-T covariances, equivalent to the corrected implementation.

| Portfolio family | Model | GRS: before → after | p-value: before → after |
| --- | --- | --- | --- |
| Size × B/M | CAPM | 2.902377 → 2.910331 | 3.64127e-06 → 3.41998e-06 |
| Size × B/M | FF3 | 2.536136 → 2.550090 | 6.11813e-05 → 5.50973e-05 |
| Size × B/M | FF5 | 2.124628 → 2.142056 | 0.00119029 → 0.00105547 |
| Size × INV | CAPM | 4.215741 → 4.226911 | 6.43582e-11 → 5.84675e-11 |
| Size × INV | FF3 | 4.169903 → 4.192100 | 9.58938e-11 → 7.92652e-11 |
| Size × INV | FF5 | 2.955606 → 2.979059 | 2.33796e-06 → 1.94005e-06 |
| Size × OP | CAPM | 1.770782 → 1.775634 | 0.0119396 → 0.0115904 |
| Size × OP | FF3 | 1.925609 → 1.936204 | 0.00450283 → 0.00420342 |
| Size × OP | FF5 | 1.144376 → 1.153763 | 0.285476 → 0.275518 |
| Size × B/M × INV | CAPM | 2.784937 → 2.792569 | 8.78131e-07 → 8.16252e-07 |
| Size × B/M × INV | FF3 | 2.605099 → 2.619432 | 4.82186e-06 → 4.21751e-06 |
| Size × B/M × INV | FF5 | 2.075511 → 2.092536 | 0.000532371 → 0.000461766 |
| Size × B/M × OP | CAPM | 1.958450 → 1.964098 | 0.00141219 → 0.00134973 |
| Size × B/M × OP | FF3 | 1.837612 → 1.848252 | 0.00363994 → 0.00335498 |
| Size × B/M × OP | FF5 | 1.491424 → 1.504296 | 0.0414565 → 0.038204 |
| Size × OP × INV | CAPM | 4.160508 → 4.171910 | 7.93796e-13 → 7.04511e-13 |
| Size × OP × INV | FF3 | 3.976501 → 3.998380 | 5.45697e-12 → 4.3461e-12 |
| Size × OP × INV | FF5 | 2.228801 → 2.247084 | 0.000144357 → 0.000123128 |

## Notebook 04: stock momentum and performance

The calendar-gap correction changes 2,442 of 8,880 monthly decile returns and 533 of 888 WML returns. Maximum absolute changes are 1.576598 percentage points for a decile return and 1.178107 percentage points for WML. The largest WML change occurs in February 2002: 15.554484% → 14.376377%. This removes signals whose observation lag did not match the intended calendar lag; the eleven-month 12–2 lookback and intentional skipped month are unchanged.

The stock-performance sample remains January 1951–December 2024 (888 months); model pricing remains July 1963–December 2024 (738 months). No dates were added or removed.

| Decile | Mean monthly return before (%) | After (%) |
| --- | --- | --- |
| 1 | 0.348315 | 0.349580 |
| 2 | 0.745230 | 0.745392 |
| 3 | 0.887837 | 0.885491 |
| 4 | 0.956662 | 0.955100 |
| 5 | 0.928740 | 0.931641 |
| 6 | 0.999714 | 0.997949 |
| 7 | 1.003125 | 1.000907 |
| 8 | 1.122428 | 1.124417 |
| 9 | 1.161593 | 1.164398 |
| 10 | 1.574745 | 1.573794 |

| Portfolio | Quantity | Before | After |
| --- | --- | --- | --- |
| Winners | Monthly mean (%) | 1.574745 | 1.573794 |
| Winners | Arithmetic annualized mean (%) | 18.896941 | 18.885526 |
| Winners | Annualized raw-return volatility (%) | 20.533321 | 20.530242 |
| Winners | Annualized Sharpe | 0.920306 | 0.724451 |
| Winners | HAC t(raw-return mean) | 7.773854 | 7.769023 |
| Winners | Raw-return skewness | -0.385147 | -0.384314 |
| Winners | Maximum drawdown (%) | -51.923922 | -51.965032 |
| Losers | Monthly mean (%) | 0.348315 | 0.349580 |
| Losers | Arithmetic annualized mean (%) | 4.179784 | 4.194964 |
| Losers | Annualized raw-return volatility (%) | 27.277507 | 27.276795 |
| Losers | Annualized Sharpe | 0.153232 | 0.007410 |
| Losers | HAC t(raw-return mean) | 1.264680 | 1.271758 |
| Losers | Raw-return skewness | 0.738239 | 0.742962 |
| Losers | Maximum drawdown (%) | -93.540170 | -93.369914 |
| WML | Monthly mean (%) | 1.226430 | 1.224214 |
| WML | Arithmetic annualized mean (%) | 14.717157 | 14.690562 |
| WML | Annualized raw-return volatility (%) | 23.457337 | 23.454985 |
| WML | Annualized Sharpe | 0.627401 | 0.626330 |
| WML | HAC t(raw-return mean) | 5.447228 | 5.447310 |
| WML | Raw-return skewness | -1.394457 | -1.394668 |
| WML | Maximum drawdown (%) | -81.032682 | -80.846039 |

The large winner/loser Sharpe changes primarily reflect subtracting RF, rather than momentum reclassification. With corrected portfolios but the old raw-return Sharpe calculation, the values would be 0.919888 and 0.153792; the corrected excess-return values are 0.724451 and 0.007410. WML remains self-financing and receives no further RF subtraction. Means, volatility, mean t-statistics, skewness and drawdowns in the long-only performance rows still describe raw returns, as explicitly stated in the notebook.

All three stock maximum-drawdown changes arise from changed momentum returns. Including initial wealth does not change their worst drawdown values in this sample.

WML–UMD correlation: 0.898479 → 0.898692. Official UMD mean remains 0.658232% monthly.

### Momentum-decile model tests

Both added factors still reduce FF5 pricing errors, UMD still gives smaller errors than FMOM, both augmented P10−P1 alphas remain significant, and GRS still rejects all three models. The notebook updates the quoted numerical estimates.

| Model | Quantity | Before | After |
| --- | --- | --- | --- |
| FF5 | Mean \|alpha\| (% monthly) | 0.24694 | 0.247949 |
| FF5 | P10 − P1 alpha (% monthly) | 1.33684 | 1.33585 |
| FF5 | NW t(spread alpha) | 4.1895 | 4.19341 |
| FF5 | Average adjusted R² | 0.810148 | 0.810118 |
| FF5 | GRS statistic | 4.41677 | 4.39869 |
| FF5 | GRS p-value | 4.75906e-06 | 5.10678e-06 |
| FF5 + UMD | Mean \|alpha\| (% monthly) | 0.125216 | 0.124208 |
| FF5 + UMD | P10 − P1 alpha (% monthly) | 0.30826 | 0.307471 |
| FF5 + UMD | NW t(spread alpha) | 2.99422 | 2.98858 |
| FF5 + UMD | Average adjusted R² | 0.900925 | 0.900886 |
| FF5 + UMD | GRS statistic | 3.55215 | 3.48243 |
| FF5 + UMD | GRS p-value | 0.00013159 | 0.000170965 |
| FF5 + FMOM | Mean \|alpha\| (% monthly) | 0.129601 | 0.128476 |
| FF5 + FMOM | P10 − P1 alpha (% monthly) | 0.806793 | 0.805933 |
| FF5 + FMOM | NW t(spread alpha) | 3.04566 | 3.04835 |
| FF5 + FMOM | Average adjusted R² | 0.849405 | 0.849372 |
| FF5 + FMOM | GRS statistic | 3.32081 | 3.29554 |
| FF5 + FMOM | GRS p-value | 0.00031231 | 0.000342965 |

GRS changes combine normalization and changed test-asset returns. Holding the old momentum portfolios fixed isolates normalization:

| Model | Original GRS | Normalization only | Normalization + calendar correction |
| --- | --- | --- | --- |
| FF5 | 4.416766 | 4.452407 | 4.398693 |
| FF5 + UMD | 3.552154 | 3.585605 | 3.482430 |
| FF5 + FMOM | 3.320812 | 3.352123 | 3.295544 |

All 30 portfolio regression result rows were compared, including alpha, alpha SE/t/p-value, every loading and its SE/t-statistic, R², adjusted R² and observation count. Maximum absolute alpha changes are 0.004274, 0.004311 and 0.004248 percentage points monthly for FF5, FF5 + UMD and FF5 + FMOM, respectively. No loading crosses the plotted |t| = 1.96 threshold. One individual-alpha decision changes: P7 under FF5 + FMOM has alpha −0.094204% → −0.097359%, t −1.931429 → −1.982957, and p 0.053430 → 0.047372. The notebook identifies this marginal 5% rejection.

Unchanged: the size lead–lag exercise; official UMD CAPM/FF3/FF5 regressions; factor-continuation statistics; all factor-momentum horizon returns and summaries; signal-sorted factor summaries; FMOM model regressions; and the final UMD/FMOM spanning tests. FMOM construction, Sharpe ratios, drawdowns and the directional spanning conclusion are unchanged.

## Notebook 05: initial wealth in drawdowns

The sole numerical change is the first market drawdown in the common-volatility plot sample, January 1927: 0% → −0.044167%. The plotted PNG is unchanged at the existing resolution. Maximum drawdowns are unchanged: market −84.634149%, momentum −78.437148%, and volatility-managed momentum −32.282494%. Sharpe ratios, loss quantiles, expected shortfall, skewness, kurtosis, growth indices, construction checks and every regression result are unchanged. No empirical interpretation needed revision.

The common six-factor comparison still uses August 1963–July 2026 (756 months); the downside comparison still uses January 1927–July 2026 (1,195 months). Ex-post normalization and prepared managed-factor returns were preserved.

## Sample and definition checks

- GRS uses one complete common sample per portfolio family and model comparison; individual alpha inference remains HAC with 12 monthly lags. Conventional GRS retains its iid/normality assumptions and is not a HAC test.
- Long-only test assets subtract aligned RF; WML, UMD, FMOM and managed factor excess returns receive no additional RF subtraction. Arithmetic annualization and sample-standard-deviation Sharpe calculations are preserved.
- Momentum retains NYSE decile breakpoints, lagged value weights, eleven returns from t−12 through t−2, and one-month holding. No accounting eligibility or benchmark definitions changed.
- Drawdown peaks include initial wealth W₀ = 1. Factor cumulative paths remain normalized growth indices with the existing leverage/cost caveats.
- Maximum-Sharpe and tangency corrections are not invoked in these notebooks and therefore have no empirical consequences here.

Notebook 03 samples (each identical before and after):

| Family | Months | Start | End |
| --- | --- | --- | --- |
| size_bm | 726 | 1964-07-01 | 2024-12-01 |
| size_inv | 750 | 1962-07-01 | 2024-12-01 |
| size_op | 726 | 1964-07-01 | 2024-12-01 |
| size_bm_inv | 726 | 1964-07-01 | 2024-12-01 |
| size_bm_op | 690 | 1967-07-01 | 2024-12-01 |
| size_op_inv | 726 | 1964-07-01 | 2024-12-01 |

## Validation and remaining decisions

All original and corrected notebook runs completed without errors. Regenerated notebooks retain cell IDs, section order, code-cell counts (7/15/6) and figure counts (8/5/7). Only the stock-momentum profile and alpha/loading figure change in their PNG output. Full test suite: **52 passed**. All 21 empirical GRS values also match an independent QR-fit/divisor-T calculation, with maximum absolute error 1.89e-13. Notebook files validate as nbformat v4.

Remaining methodological decisions are unchanged: generic characteristic/weight/investment shifts are observation-based; Notebooks 03–04 use the existing FF5-SMB three-factor benchmark; factor availability can depend on current-return missingness; conventional GRS assumptions are stronger than HAC inference; volatility normalization is ex-post. At this validation stage, broader exposition and reference refinement were deferred; subsequent refinements preserved executable cells and saved outputs.

## Prepared input checksums

All five input checksums were identical before and after execution. Paths below are relative to the parent project directory.

| Prepared input | SHA-256 |
| --- | --- |
| 01_complete/fama-french-five-factor-replication/data/interim/Python/ff5_factors_internal.parquet | db605ce318b430243e2f759c31c07137404fdcc18a140db58b76d4bdc5011647 |
| 01_complete/fama-french-five-factor-replication/data/interim/Python/ff5_test_portfolios.parquet | 8c53124f1a5f502433237ddc73a99055bf550e71d646435db04d58b8412deff7 |
| 01_complete/fama-french-five-factor-replication/data/interim/Python/ff_2x4x4_test_portfolios.parquet | 9a7bceeef180d4f0f95c87cad5c199c419b773200f9bba230a91ea1c5afee097 |
| 01_complete/fama-french-five-factor-replication/data/interim/Python/crsp_compustat_monthly_panel_1950_2024.parquet | 9a364de8a31d550db55898b4bdf693f17bdc196195b6c0a7e7cabcdd3ae33b0c |
| 01_complete/volatility-management-and-liquidity/data/processed/managed_factors.parquet | 786af49c080bdc6a1114df8daaf5f35464979d7b59b8a37659f44ff64dabeeda |
