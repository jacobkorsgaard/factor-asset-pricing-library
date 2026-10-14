# Original WRDS preparation and notebooks 00–03

Validated 14 October 2026. This record supports later README work. The main README
and notebooks 04–09 are unchanged from the start of this migration; no
`data/README.md` was recreated. Neither companion repository was modified.

## Workflow and implementation

1. Run `notebooks/00_crsp_compustat_data_preparation.ipynb` from the four original
   exports in `data/raw/wrds`. It demonstrates source inspection, CRSP cleaning,
   annual Compustat selection, dated CCM linking, July accounting carriers, RF
   conversion, diagnostics and local persistence. No live WRDS connection is used.
2. 01 reads the locally generated panel and separate annual accounts, measures the
   June 2020 cross-section with the existing characteristics API, and independently
   verifies size/BM/OP/INV arithmetic for every eligible security.
3. 02 preserves the June independent-versus-conditional illustration, then builds
   all three historical independent 5×5 families from security observations using
   the existing annual assignment and portfolio-return APIs. It compares the 75
   resulting test portfolios with published French returns.
4. 03 constructs June 2×3 assignments, value-weighted cells, HML/RMW/CMA, three
   component SMB spreads and their equal-weight FF5 average, and the linked-universe
   market excess payoff. It checks cell-leg identities and compares with French
   FF5 using the existing validation/HAC regression functions.

`wrds_data.py` handles file reading, source hashes and cache I/O, with no financial
calculations. `data_preparation.py` supplies individual cleaners, historical
linking, dated accounting attachment, Treasury conversion and panel/weight
validation. `construction.py` is a short recipe layer composing existing
characteristic, annual-sort and portfolio-return functions; it does not reproduce
unneeded 2×4×4, forecast or replication-reporting machinery.

The sole analytical API extension is the optional `annual_data=` keyword on
`fama_french_characteristics`. Its default behavior is unchanged. Supplying clean
original annual records removes the dependence on retrospective monthly carriers,
requires consecutive fiscal years for investment, and prevents later calendar-year
statements from being assigned to earlier FYEAR+1 formation years. Financial
formulas continue to use the existing book-equity, profitability and investment
functions. Portfolio and factor APIs are unchanged.

Local artifacts are `data/processed/crsp_compustat_monthly.parquet`,
`compustat_annual.parquet` and `wrds_preparation.json`. The JSON contains source
SHA-256 hashes, preparation version and aggregate diagnostics. Loaders reject
missing/stale manifests instead of falling back to companion intermediates. Future
changes to preparation conventions should increment `CACHE_VERSION` and rerun 00.
The annual cache is necessary because June formation must not depend on a future
July carrier existing for that security. No precomputed portfolio or factor cache
is required.

Executed notebooks are retained locally in `data/processed/notebook_runs/`.
Source notebooks 00–03 have outputs and execution timestamps cleared so restricted
observations and derived return paths are not included in repository artifacts.
Original exports, caches and executed notebooks remain ignored by Git. Tests use
synthetic observations only.

## Sources and required variables

| Dataset / supplied filename | Variables and units |
| --- | --- |
| `CRSP-1950_01-2024_12.csv` | PERMNO, date, SHRCD, EXCHCD, RET, DLRET, PRC, SHROUT. RET/DLRET: decimal simple returns; PRC: dollars with possible negative quotation flag; SHROUT: thousands. |
| `Compustat-1950_06 - 2024_12.csv` | GVKEY, DATADATE, FYEAR, AT, SEQ, TXDITC, PSTKRV, PSTKL, PSTK, REVT, COGS, XSGA, XINT. Accounting amounts: millions. INDFMT/DATAFMT/CONSOL/CURCD verify INDL/STD/C/USD selection; COSTAT is not restricted to active companies. |
| `Merger CRISPxCompustat.csv` | GVKEY, LINKPRIM, LINKTYPE, LPERMNO, LINKDT, LINKENDDT. LPERMCO/LIID exist but are not used for this security-level construction. |
| `CRSP - Riskfree - 1950_01_01 - 2024_12_31.csv` | MCALDT and TMYTM; yield in annual percent. Other Treasury fields identify instruments but do not enter the retained conversion. |

These are licensed local exports, not public download URLs. All supplied files
are RTF-wrapped numeric CSVs. The reader strips wrapper controls/row terminators in
a temporary stream before parsing, preserves scientific notation and zero-padded
GVKEYs, checks required headers, and leaves original bytes untouched. It is not a
general RTF/document converter. Source hashes in the local preparation manifest
identify this snapshot; the source filenames alone do not establish vintage.

Public validation uses the existing `french_data.py` loader and original files
under `data/raw/french`. Exact official URLs and hashes remain in
[french-source-manifest.csv](french-source-manifest.csv). Relevant sources are
monthly FF5 and the three 25-portfolio Size × B/M, OP and INV families. Definitions:
[French FF5 documentation](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html).
Official security-level accounting characteristics are not publicly supplied by
these return files; security measurements are compared with the original
replication and explicit formulas, while portfolios and factors are compared with
French.

## Retained definitions and explicit restrictions

- CRSP records, not whole security histories, are filtered to exchange codes 1/2/3
  and share codes 10/11. Security/month keys must be unique. Negative PRC flags are
  retained; market equity is absolute price times positive shares. Recognized
  return flags/sentinels become missing. Unknown codes or returns below −100%
  raise. Delisting-adjusted returns compound RET and DLRET, retaining either when
  only one is observed. Missing delisting payoffs are not imputed.
- Dates are month starts; monthly returns remain decimals. Market equity is in
  thousands and is divided by 1,000 for comparison with accounting millions.
  Market cap remains security-level: no PERMCO share-class aggregation is inferred.
- Historical CCM types LU/LC/LN/LS and primary indicators P/C match the reference.
  Intervals are evaluated at month starts, inclusive. Missing/.B starts and
  missing/.E ends are open; malformed dates raise. Prefer P over C, LU over LC over
  LN over LS, then the latest start. Equally preferred conflicting company IDs
  raise. Unlinked securities remain excluded from the local market proxy.
- Compustat uses latest DATADATE per GVKEY/FYEAR after exact-duplicate and format
  selection. Conflicting latest statements raise. Fiscal history is independent
  of the security panel. No active-only or future-survival restriction is added.
- Calendar-year accounts enter monthly carriers in the following July and expire
  after the following June. FYEAR+1 remains the reference characteristic formation
  convention, but statements dated in a later calendar year cannot enter that
  earlier formation. **This conservative guard leaves those mismatched fiscal
  records unassigned for that characteristic formation; it does not implement a
  new calendar-year reallocation scheme.** There are 66,645 fiscal/calendar
  mismatches in the annual table. Historical filing dates and accounting revisions
  cannot be verified by these exports.
- Book equity = SEQ + missing-TXDITC-as-zero − preferred stock, with PSTKRV, PSTKL,
  then PSTK preference; missing preferred stock is zero, and nonpositive BE is
  missing. No alternative equity fallback is introduced. OP requires REVT, COGS
  and positive BE, with missing XSGA/XINT treated as zero. This differs from French's
  published expense-availability rule. INV uses positive lagged assets and a
  consecutive fiscal-year pair; negative or missing investment is not zero-filled.
- June size and December t−1 ME supply formation characteristics. Current June
  eligibility explicitly checks prior December presence and positive June ME.
  The old holding-year `has_dec`/`has_june` flags are not reused to identify current
  June formation history. Those flags in the reference select December t−2 and
  June t−1 when evaluated on June t, adding unintended history restrictions.
- NYSE breakpoints apply to the broader linked exchange universe. 5×5 quintiles
  and characteristic 30/70 thresholds use lower interpolation and equality enters
  the lower group. FF5 size uses the actual NYSE median, including an even-sample
  midpoint, rather than the generic lower 50% order statistic. Families can have
  different characteristic eligibility; one common size split is retained.
- Assignments begin July and last through the following June. Value weights use
  ME from exactly the preceding calendar month; missing months invalidate weights.
  Missing realized returns are omitted and observed weights renormalized, as in
  the existing aggregation API. This is an available-return convention, not a
  complete implementable policy for missing payoffs. Factors require their stated
  cells; missing cells are not replaced by an average of fewer required cells.
- RF = exp((TMYTM/100)×30/365)−1, averaged across observed Treasury instrument
  records per month. The export has 86 undated instrument placeholders with no
  yield, which are removed. This is the reference yield proxy, not an observed
  one-month Treasury holding-period return or French RF. Portfolio total returns
  subtract RF once; long–short factors already cancel common RF.

## Validation and differences

**88 tests passed**, including 21 new preparation cases covering original plain/
RTF ingestion, identifiers/scientific notation, CRSP flags/units/filtering,
conflicting accounts, link priorities/endpoints, month-start boundaries, accounting
availability/expiry, fiscal-year gaps, formation timing, exact calendar weights,
size-median behavior, panel integrity and stale-cache rejection. Four non-failing
pandas FutureWarnings come from the existing characteristic flag-filling code.

All four notebooks executed in Jupyter from a fresh isolated directory containing
only this library, the notebooks and original WRDS/French sources: no pre-existing
processed datasets and no companion repository. Notebook 00 rebuilt the caches;
01–03 then used them. There were no cell errors; six figures rendered and were
inspected. The run used Python 3.11 in the installed anaconda-finance kernel.

Before editing, the old notebooks 01–03 were executed against the existing
replication inputs and their outputs captured temporarily for comparison. Reading
those inputs for validation does not create a workflow dependency. The comparison
script did not import the reference `config.py` or run its pipeline, so no
companion artifacts were written.

| Diagnostic | Result |
| --- | ---: |
| Raw CRSP / eligible exchange-share rows | 4,934,717 / 3,613,067 |
| Clean annual accounts | 516,465 (11 excluded/duplicate rows) |
| Eligible CCM links | 31,931 |
| Linked security-months | 3,262,249, January 1950–December 2024 |
| Distinct securities / companies | 22,830 / 22,649 |
| Unlinked eligible CRSP rows excluded | 350,818 |
| Linked rows with accounts / expired carriers removed | 3,162,926 / 8,324 |
| Missing adjusted returns / missing market equity | 14,117 / 27,969 |
| Monthly RF coverage | Complete |

**Historical endpoint correction:** the reference RTF reader leaves the final
field's trailing backslash on LINKENDDT. None of its 32,435 nonmissing end strings
parse as dates; coercion then makes them open-ended. Correct parsing recovers
25,832 closed endpoints among eligible links. The new panel removes **18,643**
legacy security-months, every one after its recorded link end. Another **8,157**
common security-months select a different company once expired links are excluded.
This is an identified ingestion correction, not a source-vintage inference.

For the June 2020 illustration, positive-capitalization securities decline from
3,519 to 3,496. Valid BM/OP/INV counts change from 2,934/2,965/3,137 to
2,925/2,958/3,133. Size, BM, OP and INV agree exactly on all common-valid rows
(maximum absolute difference zero); changed links/eligibility alter missingness.
Independent-versus-conditional BM reassignment changes from 1,617 of 2,934 to
1,631 of 2,925 eligible securities. The theory and figure layouts are preserved.

Historical family date bounds remain unchanged: BM and OP begin July 1960
(774 months through December 2024); INV begins July 1952 (870 months). Individual
cells still have differing availability. On matched portfolio-month cells,
correlations with the old replication are 0.989 BM, 0.984 OP and 0.990 INV. Mean
absolute return differences are **0.506, 0.551 and 0.501 percentage points monthly**;
maximum absolute differences reach **38.42, 52.61 and 22.30 points**, respectively.
All three maximum differences occur in January 2021. The relevant constructed cells contain hundreds or over a hundred securities, so these are not merely empty-cell artifacts. These material extreme-cell differences are reported, not concealed. The endpoint
correction, direct annual histories, fiscal/calendar guard, annual-gap requirement,
current formation history and calendar-exact weights jointly change membership;
this comparison does not separately attribute each portfolio return difference.

The factor common sample remains July 1962–December 2024, 750 months. Matching
French FF5 uses July 1963–December 2024, 738 months. Cell-leg identities, FF5 SMB
component averaging, moment calculations and cumulative index recurrences pass.

| Factor | Previous mean (% monthly) | Local mean (% monthly) | Correlation with previous | Correlation with French | Local−French mean (pp monthly) |
| --- | ---: | ---: | ---: | ---: | ---: |
| MKT | 0.608 | 0.608 | 0.99999 | 0.99983 | −0.0031 |
| SMB | 0.221 | 0.226 | 0.99407 | 0.99334 | 0.0331 |
| HML | 0.198 | 0.217 | 0.98811 | 0.97562 | −0.0407 |
| RMW | 0.301 | 0.345 | 0.97574 | 0.96444 | 0.0573 |
| CMA | 0.222 | 0.243 | 0.97049 | 0.97758 | −0.0043 |

Previous/local means above use the 750-month common construction sample; French
comparisons use the 738-month overlap. Official-factor spanning alphas for SMB
and RMW reject zero individually at nominal 5% (NW statistics 2.22 and 2.29).
High correlation therefore does not establish identical payoffs. Median
within-portfolio correlations with French are 0.977 BM, 0.982 OP and 0.990 INV;
minimum correlations are 0.938, 0.854 and 0.985, respectively. Numeric notebook
commentary was updated to the current snapshot, including the now slightly
positive largest-size BM endpoint difference.

No statistic is forced to match either source. Beyond the identified parser and
calendar-integrity corrections, differences can reflect linked-universe scope,
security versus company capitalization, expense eligibility, missing-cell policies,
RF/yield definitions and export/French vintages. The French inputs retained from
the earlier migration mix May 2026 portfolio and August 2026 factor vintages.
Their current histories use revised data, so these comparisons do not establish
point-in-time equivalence or an exact French replication.

## Reproducibility and later documentation

Record the four licensed source files/variables/units, absence of live WRDS access,
RTF reader scope, share/exchange and statement filters, CCM priorities/boundary
convention, accounting-window/FYEAR assumptions, consecutive-year/month rules,
security-level capitalization, NYSE median/quantiles, July–June membership, RF
conversion, complete 00→01→02→03 execution order, cache hashes/version checks and
local-only outputs. Users must obtain their own licensed exports and have a Parquet
engine installed. The preparation manifest has the exact original-byte hashes.

Historical filing dates, accounting revisions, delisting imputation, company-level
share-class aggregation, alternative French eligibility and real-time trading
frictions remain outside this compact workflow. Later notebooks 04–09 retain
published French inputs and were not changed by this task. Neither README was edited.
