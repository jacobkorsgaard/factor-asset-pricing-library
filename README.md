# Factor Asset Pricing

> **Status: experimental first draft (`v0.1.0`).** The package collects
> reusable methods from validated empirical projects, but its API may change as
> the individual modules receive further review and notebook examples are
> developed.

A compact Python library for standard empirical asset-pricing work. The code
uses ordinary pandas objects and keeps portfolio formation, timing, and
weighting choices visible in function arguments.

The library is a methodological toolkit, not a replacement for complete
empirical replication projects. Data acquisition, CRSP--Compustat linking, and
project-specific sample construction remain outside its scope.

## Modules

- `characteristics.py`: CRSP return and market-equity definitions plus standard
  Fama--French book equity, book-to-market, profitability, and investment.
- `sorts.py`: one- to three-way independent or sequential quantile sorts,
  reference-universe breakpoints, characteristic lags, and EW/VW returns.
- `factors.py`: long-short spreads, quantile factors, Fama--French 2x3 factors,
  and the market excess return.
- `momentum.py`: stock momentum and factor momentum with configurable lookback,
  skip, and overlapping holding periods.
- `test_assets.py`: sorted test portfolios, average characteristics, and excess
  returns, all reusing the sorting module.
- `asset_pricing_tests.py`: OLS/HAC time-series regressions, GRS and spanning
  tests, Sharpe ratios, and maximum-Sharpe comparisons.
- `volatility_management.py`: lagged realized variance/volatility and inverse-
  variance or inverse-volatility scaling.
- `mean_variance.py`: classical portfolio moments, 1/N, GMV, tangency,
  efficient-frontier calculations, and plotting.

## Understanding the code

The [source code guide](docs/code-guide.md) explains the responsibility and
data flow of every module for readers who did not write the package. The
[methodology notes](docs/methodology.md) explain why the central empirical
choices are made, including information timing, breakpoint universes,
Newey--West inference, GRS assumptions, overlapping momentum returns, and
lagged volatility scaling.
The [provenance and alignment notes](docs/provenance.md) record which functions
come directly from the companion projects and which are generalized library
interfaces.

The source modules contain the implementation and API documentation. Future
examples and notebooks should call those functions rather than recreating the
calculations. Notebook structure will be designed separately after the initial
source API has been reviewed and stabilized.

## Installation

Clone the repository and create an isolated environment:

```bash
git clone https://github.com/jacobkorsgaard/factor-asset-pricing-library.git
cd factor-asset-pricing-library
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

The editable installation means changes under `src/` are immediately available
to scripts using the same environment. Verify the installation with:

```bash
python -c "import factor_asset_pricing; print(factor_asset_pricing.__file__)"
```

For development and tests, install the optional test dependency and run pytest:

```bash
python -m pip install -e ".[test]"
pytest -q
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1` instead of `source .venv/bin/activate`.

## Timing conventions

`portfolio_returns(..., weighting="vw")` lags market equity within security by
default. `lag_characteristics` makes monthly signal lags explicit. For annual
Fama--French sorts, pass a point-in-time formation sample or an already stable
formation-year characteristic with `formation_col`; portfolio labels can then
be merged onto the subsequent holding-period panel. Breakpoints use pandas'
`interpolation="lower"`, and observations equal to a breakpoint enter the lower
portfolio, following the reference replication.

Momentum signals use only completed return observations. Volatility-managed
returns use lagged realized measures. Full-sample volatility normalization is
available for replication comparisons and should not be interpreted as a
real-time volatility target.

Fama--MacBeth cross-sectional regressions are intentionally out of scope for
this first version and are a natural future extension.

## License

The source code and original documentation are released under the MIT License.
Third-party datasets remain subject to their respective providers' terms.
