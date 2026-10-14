# Final reproducibility and data-transparency audit

14 October 2026. **The current fixed-input workflow is reproducible without either
companion repository.** Publication documentation remains pending: the main README
still describes companion-prepared inputs and independent notebook execution, and
`data/README.md` is intentionally absent. Neither README was changed or created.
No additional data-handling error required a code or notebook change in this audit.

## Findings against the requested checks

| Check | Confirmed result | Qualification |
| --- | --- | --- |
| 1. Original WRDS workflow | 00 reads four original local exports; 01–03 use only its reproducible monthly/annual caches. | 02/03 also read public French validation benchmarks. Own licensed exports are required. |
| 2. Public workflow | 04–09 execute entirely from original French CSV/ZIP sources. | 08 analyzes published stock-momentum portfolios; security assignments/alternative CRSP holdings cannot be rebuilt publicly. |
| 3. No companion Parquet | Static checks found no legacy paths/names. Instrumented execution rejected external Parquet reads; only 01–03 made local-cache reads. | Previously captured companion comparisons are documentation evidence, not runtime inputs. |
| 4. Source/transform traceability | All 14 French tables match recorded hashes/coverage and current official catalogue URLs. Four WRDS hashes identify the exact input bytes; required fields and transformations are documented. | Original WRDS extraction SQL/table versions and database vintage are not recoverable from the supplied files. |
| 5. Units/dates/timing | Decimal simple returns, month-start labels, observed daily dates, unit scaling, RF handling, June formation and calendar-exact lagged weights are consistent in the applications. | Samples, SMB definitions, Treasury/French RF and source vintages intentionally differ; they must not be represented as one universal dataset. |
| 6. Methods/explanations | All 88 original display equations in 01–09 are retained. Educational objectives and analytical APIs remain; empirical commentary reflects the migrated results. | Documented changes include public portfolios in 08 and the WRDS parser/calendar-integrity corrections. Exact former security-level exercises are not claimed. |
| 7. Disposable caches | A cache-free build exactly reproduced both existing tables; deleting both rebuilt tables and their manifest, then rerunning 00, reproduced them exactly again. | Equality covers values, keys, column order and dtypes from fixed originals; not arbitrary new exports, rolling downloads or cross-version binary files. |
| 8. Tests/execution | 88 tests passed; all ten notebooks executed without errors, rendering 34 figures. All 47 compared saved tabular outputs matched. | Existing pandas flag-filling emits four non-failing FutureWarnings in tests. |
| 9. Git exclusions | All 38 current raw/processed artifacts, including local audit evidence, are ignored; no current data observations are tracked under those directories. 00–03 source outputs remain cleared. | This checks current paths/output policy, not a historical Git-history purge. |

## How execution and regeneration were verified

A fresh disposable workspace received only current library/notebook sources and
copies of the original WRDS/French files. It began with no Parquet tables or
preparation manifest. All ten notebooks were executed there in separate Jupyter
kernels. Audit-only guard cells disabled French network downloads and rejected
Parquet reads outside that workspace's `data/processed` directory. Repository
notebooks were not edited to add these guards.

00 read no Parquet. 01 read its two local tables; 02 read them for both its snapshot
and historical construction; 03 read the two local tables. 04–09 read no Parquet.
No live WRDS connection or companion directory was present.

Both generated tables passed exact DataFrame equality against the project's local
caches: **3,262,249 security-months / 31 columns** and **516,465 annual records /
16 columns**. The security panel passed historical CCM bounds, accounting-window,
unique-key, month-start and RF checks. It contains 900 calendar months and one
consistent RF value per month. Missing security returns/market equity remain
visible rather than filled.

Next, only the disposable copies of the two caches and `wrds_preparation.json`
were deleted. Loading then raised the expected instruction to run notebook 00.
Rerunning 00 regenerated the same values and dtypes and the same original-source
hashes. No source files or project caches were deleted. Since the tables are
identical, downstream analysis receives identical inputs; the first full run also
matched 47 saved tabular outputs, including the migrated factor/portfolio validation.

The source check uses the live [official French catalogue](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
The inventory is [french-source-manifest.csv](french-source-manifest.csv); the
transformation and comparison details are in
[French migration](french-data-migration.md) and [WRDS migration](wrds-data-migration.md).
The unused RTF “FF5 Download” is explicitly excluded from ingestion.

Notebook execution used Python 3.11.13, pandas 2.3.2, NumPy 2.3.3, SciPy 1.16.1,
statsmodels 0.14.5, Matplotlib 3.10.6, PyArrow 25.0.0 and IPython 9.1.0 in the
installed `anaconda-finance` kernel. Tests used Python 3.13.5, pytest 8.3.4,
pandas 2.2.3 and NumPy 2.1.3. Other environments were not freshly certified here.

The tested execution pattern was:

```bash
python -m pytest -q
mkdir -p data/processed/notebook_runs
jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.kernel_name=anaconda-finance \
  --ExecutePreprocessor.timeout=300 \
  --output-dir data/processed/notebook_runs notebooks/*.ipynb
```

Use the kernel installed in the target environment; `anaconda-finance` is the
local audit kernel, not a package requirement. Execute source notebooks from the
repository/root notebook workflow; saved executed copies are review artifacts.
Audit evidence and executed copies are retained locally under ignored
`data/processed/final_audit/`.

## Remaining limits, distinct from reproducibility

- Reproduction starts from the supplied licensed WRDS exports. It does not recreate
  the original WRDS extraction query or verify historical filing/restatement vintages.
- FYEAR+1 and assumed July availability are retained. Fiscal/calendar mismatch
  records are excluded for that formation, rather than reassigned under a new
  calendar-year rule. Formation-year characteristic fields are consumed at June
  formation, not certified as available trading signals in every preceding month;
  monthly accounting carriers have their separate July–June window.
- The local market remains a linked security universe with security-level ME and
  the reference Treasury-yield RF proxy. Accounting expense eligibility, missing
  returns/cells and weighting conventions prevent a claim of exact French replication.
- 08's public decile WML/2×3 UMD comparison preserves the return-analysis objective,
  not the unavailable security-level construction. Annual public size quintiles
  also replace the earlier monthly linked-universe sorts.
- French inputs mix May/August 2026 vintages and revised histories. Hashes identify
  the validated originals; rolling URLs and replacement files can change even a
  fixed historical sample. The French manifest is provenance metadata, not a
  runtime version-lock mechanism. Preserve local originals for this snapshot.
- 09 retains daily demeaned variance sums, a calendar-month lag, April 2015 ex-post
  calibration, uncapped exposure and sample-specific plot rescaling. These do not
  establish real-time investability or account for financing/trading costs.

The precise later-documentation scope is in the
[README checklist](readme-documentation-checklist.md). No library expansion,
notebook redesign, README edit, or new data README was needed for this audit.
