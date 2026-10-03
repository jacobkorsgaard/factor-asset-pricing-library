# Factor Asset Pricing

> **Status: experimental first draft (`v0.1.0`).** The package collects
> reusable methods from validated empirical projects, but its API may change as
> the individual modules receive further review and notebook examples are
> developed.

A compact Python library focused primarily on empirical factor asset pricing
and the cross-section of equity returns. It provides reproducible implementations
of characteristic construction, portfolio sorts, factor returns, validation,
and standard asset-pricing tests. The code uses ordinary pandas objects and
keeps information timing, portfolio formation, and weighting choices visible
in function arguments.

The repository is not intended to be a complete treatment of asset-pricing
theory. Its narrower aim is to connect transparent empirical methods with the
economic questions that motivate factor research.

The library is a methodological toolkit, not a replacement for complete
empirical replication projects. Data acquisition, CRSP--Compustat linking, and
project-specific sample construction remain outside its scope.

## Modules

- `characteristics.py`: CRSP return and market-equity definitions plus standard
  Fama--French book equity, book-to-market, profitability, and investment.
- `sorts.py`: one- to three-way quantile sorts, explicit breakpoint
  probabilities and conditioning, annual formation, and EW/VW returns.
- `factors.py`: long-short spreads, quantile factors, Fama--French 2x3 factors,
  a thin FF5 composer, and the market excess return.
- `momentum.py`: stock momentum and factor momentum with configurable lookback,
  skip, and overlapping holding periods.
- `test_assets.py`: sorted test portfolios, average characteristics, and excess
  returns, all reusing the sorting module.
- `asset_pricing_tests.py`: OLS/HAC time-series regressions, GRS and spanning
  tests, minimal Fama--MacBeth estimation, pricing errors, Sharpe ratios, and
  maximum-Sharpe comparisons.
- `validation.py`: generic aligned factor and grouped-portfolio validation.
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

The source modules contain the implementation and API documentation. The first
notebook provides a concise conceptual guide to the data-to-factor workflow.
The subsequent empirical notebooks call the package rather than recreating its
methods and progress through asset-pricing tests and dynamic strategies.

## Notebooks

1. From data to factors: a conceptual guide to characteristics and portfolio sorting
2. Factor spanning and time-series regressions
3. Multifactor model tests and cross-sectional pricing
4. Momentum in asset pricing
5. Volatility-managed factors

Notebook 1 is deliberately explanatory and contains no empirical dependency.
Notebooks 2--5 are executable empirical applications with saved outputs. They
use the reusable package functions for estimation and portfolio construction,
while prepared-data creation remains in the companion replication projects.

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

## Quick start

The API accepts ordinary pandas DataFrames. For example, a value-weighted
univariate sort can be formed as follows:

```python
from factor_asset_pricing.sorts import sort_portfolios

portfolio_returns, assignments = sort_portfolios(
    panel,
    characteristics="book_to_market",
    n_portfolios=5,
    reference="nyse",
    weighting="vw",
    return_col="ret",
    weight_col="market_equity",
    id_col="permno",
    date_col="date",
)
```

At minimum, `panel` must contain a security identifier, date, return, sorting
characteristic, and the columns required by the selected breakpoint and
weighting conventions. With the arguments above these are `permno`, `date`,
`ret`, `book_to_market`, `market_equity`, and an `exchange` column identifying
NYSE securities. Function docstrings document optional column names and return
objects; [the code guide](docs/code-guide.md) gives end-to-end usage patterns.

## Data and notebook execution

No CRSP or Compustat observations are distributed with this repository. These
datasets are licensed and users must construct an eligible, point-in-time panel
through their own WRDS access. Kenneth French benchmark files are public but
are also kept out of version control so that their provenance and vintage stay
explicit. See [data/README.md](data/README.md) for the expected inputs.

The empirical notebooks retain saved outputs so they can be read without the
underlying licensed data. Re-executing Notebooks 2--5 requires the prepared
inputs described in the data guide. Notebook 1 can be read independently, and
the Python package itself does not depend on these datasets.

## Timing conventions

`portfolio_returns(..., weighting="vw")` lags market equity within security by
default. `lag_characteristics` makes monthly signal lags explicit.
`assign_annual_portfolios` forms portfolios in one calendar month and carries
their labels through the following annual holding period. Breakpoints use
pandas' `interpolation="lower"`, and observations equal to a breakpoint enter
the lower portfolio, following the reference replication.

Momentum signals use only completed return observations. Volatility-managed
returns use lagged realized measures. Full-sample volatility normalization is
available for replication comparisons and should not be interpreted as a
real-time volatility target.

The initial Fama--MacBeth implementation uses fixed full-sample betas or fixed
supplied exposures. Rolling betas and Shanken corrections remain outside the
initial scope.

## Further reading

For broader treatments of asset-pricing theory and empirical methods, see:

- John H. Cochrane, *[Asset Pricing](https://www.johnhcochrane.com/research-all/asset-pricing)*,
  Revised Edition, Princeton University Press, 2005.
- John Y. Campbell, *[Financial Decisions and Markets: A Course in Asset
  Pricing](https://campbell.scholars.harvard.edu/publications/financial-decisions-and-markets-course-asset-pricing)*,
  Princeton University Press, 2018.
- Claus Munk, *[Financial Asset Pricing Theory](https://academic.oup.com/book/36432)*,
  First Edition, Oxford University Press, 2013.

## License

The source code and original documentation are released under the MIT License.
Third-party datasets remain subject to their respective providers' terms.
