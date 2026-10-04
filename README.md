# Factor Asset Pricing

> **Status: first public draft (`v0.1.0`).** The core methods are tested and
> drawn from validated empirical projects. The API is intentionally compact
> and may evolve as the teaching material and documentation are refined.

This repository explains and implements the empirical asset-pricing workflow
from firm characteristics and portfolio sorts through factor construction,
asset-pricing tests, and selected dynamic factor strategies:

**Firm data → characteristics → portfolio sorts → factors and test assets →
time-series tests → cross-sectional pricing → investment applications**

The repository combines three elements:

- reusable Python implementations of standard empirical methods;
- concise explanations of the assumptions and economic questions behind them;
- worked notebooks that connect the methods into a coherent research process.

The focus is **empirical factor asset pricing and the cross-section of equity
returns**, not quantitative finance generally. The aim is to make the research
choices visible: when information becomes available, which firms determine
breakpoints, how portfolios are weighted, and what an asset-pricing test does
and does not establish.

## What this repository covers

The research workflow begins by constructing point-in-time firm
characteristics and aligning them with future returns without look-ahead bias.
Securities can then be assigned to univariate or multidimensional portfolios
using NYSE, full-sample, or researcher-defined breakpoint universes. Both
independent and explicitly conditioned sorts are supported, as are equal- and
value-weighted returns and annual formation/holding periods.

Those portfolios can be used as test assets or compressed into long-short
factor returns. The library includes generic high-minus-low factors, the
Fama–French five-factor construction as a worked application, stock and factor
momentum, and validation summaries for comparing constructed returns with
external benchmarks.

Model evaluation covers time-series factor regressions, factor-spanning tests,
OLS and Newey–West/HAC inference, the Gibbons–Ross–Shanken joint test, pricing-
error summaries, and a minimal Fama–MacBeth estimator. The investment layer
adds Sharpe-ratio and classical mean–variance comparisons together with
transparent inverse-variance and inverse-volatility factor scaling.

These tools are reusable methods rather than a complete replication pipeline.
CRSP–Compustat acquisition, identifier linking, vendor-specific cleaning, and
project-specific sample construction deliberately remain outside the library.

## Start here

- **New to empirical factor research:** begin with
  [Notebook 01](notebooks/01_from_data_to_factors.ipynb), which explains the
  path from firm data to characteristics, portfolio sorts, factors, and test
  assets.
- **Interested in evaluating a new factor:** continue to
  [Notebook 02](notebooks/02_factor_spanning_tests.ipynb) for time-series
  regressions, alpha, factor loadings, and spanning.
- **Interested in testing asset-pricing models:** see
  [Notebook 03](notebooks/03_asset_pricing_model_tests.ipynb) for test assets,
  pricing errors, model fit, and joint GRS tests.
- **Interested in momentum and dynamic strategies:** see
  [Notebook 04](notebooks/04_momentum_in_asset_pricing.ipynb) and
  [Notebook 05](notebooks/05_volatility_managed_factors.ipynb).
- **Interested in implementation details:** read the
  [source code guide](docs/code-guide.md).
- **Interested in assumptions and empirical conventions:** read the
  [methodology notes](docs/methodology.md).

## Notebook sequence

The notebooks are designed as an educational progression rather than a set of
unrelated examples.

1. **[From characteristics to factors](notebooks/01_from_data_to_factors.ipynb)**
   Introduces the empirical workflow from firm data and information timing to
   characteristics, breakpoints, portfolio sorts, factors, and test assets.
   This first notebook is a conceptual guide and has no empirical-data
   dependency.

2. **[Factor regressions and spanning](notebooks/02_factor_spanning_tests.ipynb)**
   Explains how time-series regressions test whether a factor earns an average
   return beyond an existing benchmark, with emphasis on alpha, loadings,
   adjusted R², and Newey–West inference.

3. **[Multifactor models and cross-sectional pricing](notebooks/03_asset_pricing_model_tests.ipynb)**
   Compares the CAPM, FF3, and FF5 on characteristic-sorted test assets using
   portfolio alphas, pricing-error summaries, factor loadings, and GRS tests.
   The package also provides a minimal Fama–MacBeth estimator for separate
   cross-sectional applications.

4. **[Momentum](notebooks/04_momentum_in_asset_pricing.ipynb)**
   Studies momentum across stocks and factors, from lagged return relations and
   winner-minus-loser portfolios to factor-model and spanning tests.

5. **[Volatility-managed factors](notebooks/05_volatility_managed_factors.ipynb)**
   Examines dynamic factor scaling using lagged realized variance, then compares
   managed and unmanaged factors through performance and spanning regressions.

The empirical notebooks retain saved outputs and can therefore be read without
the licensed underlying data. Re-executing Notebooks 2–5 requires the prepared
inputs described in the [data guide](data/README.md).

## Repository guide

| Location | Purpose |
|---|---|
| `README.md` | Overview, intellectual storyline, and navigation |
| `notebooks/` | Worked empirical examples and teaching material |
| [`docs/methodology.md`](docs/methodology.md) | Information timing, portfolio conventions, assumptions, and econometric choices |
| [`docs/code-guide.md`](docs/code-guide.md) | Package architecture, function responsibilities, and data flow |
| [`docs/provenance.md`](docs/provenance.md) | Origins of implementations, links to companion projects, and validation status |
| `src/factor_asset_pricing/` | Reusable Python implementation |
| `tests/` | Unit tests for the public methods and empirical conventions |

The documents are intentionally complementary. Methodological explanations
belong in the methodology notes, implementation details in the code guide, and
project lineage in the provenance notes; the README provides the route through
them.

## Methodological principles

Several conventions are kept explicit throughout the library:

- characteristics must be observable before portfolio formation;
- monthly portfolio returns use lagged market equity for value weights;
- annual Fama–French-style portfolios are formed in June and held from July
  through the following June;
- breakpoint and investment universes are separate choices;
- multidimensional sorts may be independent, sequential, or explicitly
  conditioned;
- overlapping momentum portfolios require careful signal and holding-period
  alignment;
- Newey–West/HAC inference changes estimated uncertainty, not OLS coefficients;
- conventional GRS inference relies on stronger assumptions than HAC
  individual-alpha tests;
- volatility-managed returns use lagged realized risk measures.

See the [methodology notes](docs/methodology.md) for the reasoning and caveats
behind these choices. Full-sample volatility normalization is available for
replication comparisons but should not be interpreted as a real-time target.
The initial Fama–MacBeth implementation uses fixed full-sample betas or supplied
exposures; rolling betas and Shanken corrections remain outside the initial
scope.

## Python package

The package uses ordinary pandas objects and keeps timing, breakpoint,
formation, and weighting choices visible in function arguments.

- `characteristics.py`: adjusted returns, market equity, book equity,
  book-to-market, profitability, and investment.
- `sorts.py`: one- to three-way portfolio assignment, explicit breakpoint
  probabilities and conditioning, annual formation, and EW/VW returns.
- `factors.py`: generic long-short returns, quantile spreads, Fama–French 2×3
  factors, the FF5 composition layer, and the market excess return.
- `test_assets.py`: characteristic-sorted test portfolios, portfolio-average
  characteristics, and excess-return conversion.
- `asset_pricing_tests.py`: OLS/HAC regressions, spanning, GRS, minimal
  Fama–MacBeth estimation, pricing errors, and Sharpe-ratio comparisons.
- `momentum.py`: stock and factor momentum with configurable lookback, skip,
  and overlapping holding periods.
- `volatility_management.py`: lagged realized variance/volatility and inverse-
  variance or inverse-volatility scaling.
- `validation.py`: aligned factor and grouped-portfolio validation summaries.
- `mean_variance.py`: classical portfolio moments, 1/N, global minimum
  variance, tangency portfolios, and efficient-frontier calculations.

### Installation

```bash
git clone https://github.com/jacobkorsgaard/factor-asset-pricing-library.git
cd factor-asset-pricing-library
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[test]"
pytest -q
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1`. An editable installation makes changes under
`src/` immediately available to scripts and notebooks using the environment.

### Minimal example

The public API accepts ordinary DataFrames. A value-weighted univariate sort,
for example, can be formed with:

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

With these arguments, `panel` must contain `permno`, `date`, `ret`,
`book_to_market`, `market_equity`, and an `exchange` column identifying NYSE
securities. Column names and conventions are configurable; function docstrings
and the [code guide](docs/code-guide.md) describe the full interfaces.

## Data

No CRSP or Compustat observations are distributed with this repository. These
datasets are licensed, so users must construct an eligible point-in-time panel
through their own data access. Kenneth French benchmark files are public but
are kept outside version control so their source and vintage remain explicit.
The [data guide](data/README.md) lists the required prepared inputs and optional
environment variables. The Python package itself does not depend on these
datasets.

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
Third-party datasets remain subject to their providers' terms.
