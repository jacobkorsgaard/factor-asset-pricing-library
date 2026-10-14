# README documentation checklist

For later README work; neither README was changed or created during the audit.
Use the migration records for full definitions and measured comparisons.

## Main README

- [ ] Replace companion-data claims with original licensed WRDS inputs for 00–03
  and public French inputs for 04–09; 02/03 also use French validation benchmarks.
- [ ] Add notebook 00. Explain its prerequisite for 01–03, which then run
  independently; 04–09 require no WRDS preparation. Update 03 to actual factor
  construction and 08 to published stock-momentum portfolios plus constructed
  factor momentum, with its security-level limitation.
- [ ] Retain `.[notebook,test]` installation, Parquet support, kernel selection,
  root/source-notebook working directories, and explicit test/execution commands.
  Direct executed outputs to ignored `data/processed/notebook_runs`.
- [ ] Explain absent-only French downloads versus user-supplied licensed exports.
  Link the new data guide for filenames, conventions, samples and regeneration.
- [ ] Correct saved-output claims: 00–03 sources have cleared outputs; executed
  copies are local review artifacts. Distinguish MIT code from provider data terms.
- [ ] Link audit results and limitations: reproducibility from fixed originals
  does not mean exact French replication or verified point-in-time availability.

## New `data/README.md`

- [ ] Explain `raw/wrds`, `raw/french` and `processed`; distinguish preserved
  originals, disposable caches and local executed outputs, all excluded from Git.
- [ ] Inventory four WRDS exports and 14 French frequency-specific sources:
  dataset/provider, notebook uses, exact filename, required variables, units,
  coverage, vintage and hash. Give official French URLs. Mark unavailable WRDS
  extraction queries/table versions as unknown.
- [ ] Document both readers: numeric RTF unwrapping without original changes;
  French return-section selection, column mappings, sentinels, CSV-before-ZIP
  precedence and offline behavior. Identify the unused transformed “FF5 Download”.
- [ ] Specify CRSP flags/delisting compounding, price/share handling, exchange/share
  filters; Compustat format/deduplication rules; CCM intervals at month starts,
  open endpoints, priorities and ambiguity rejection. Identify linked-universe
  and security-level capitalization limits.
- [ ] Separate July–June monthly carriers from independent annual formation inputs.
  Record FYEAR+1 and fiscal/calendar mismatch exclusions, consecutive years for
  INV, BE/OP missing-input conventions and unavailable filing dates. Formation
  attributes are not generally available monthly trading signals before formation.
- [ ] State December versus June ME, NYSE median/quantiles/ties, independent versus
  illustrative conditional sorts, July–June membership, exact prior-month weights,
  missing-return renormalization and required factor cells.
- [ ] State decimal returns, month-start labels versus daily trading dates,
  thousands versus millions, Treasury-yield versus French RF, single RF subtraction,
  and FF5-derived versus conventional FF3 SMB.
- [ ] Provide exercise-specific samples: local versus public FF5 inception,
  05/07 family starts, 08 size/WML windows and signal warmups, complete cases and
  missing signal groups; 09 July 2026 endpoint and April 2015 calibration.
- [ ] Explain 08's published prior-(2,12) deciles/WML versus 2×3 Mom/UMD, annual
  size formation and unavailable CRSP assignments. Specify 09's demeaned daily
  variance sums, one-month lag, ex-post normalization, uncapped exposure and
  sample-specific plot rescaling.
- [ ] List the two Parquet caches and `wrds_preparation.json`; preserve originals,
  delete only these disposable artifacts, rerun 00, then 01–03. Explain source-hash/
  version stale-cache rejection and no companion fallback. French needs no cache.
- [ ] Record tested versions, commands, audit outcomes and material differences;
  link comparison records. Distinguish exact fixed-input rebuilds from rolling
  downloads, mixed/revised vintages, extraction/filing limitations, and numerical
  or graphical equivalence across software environments.
