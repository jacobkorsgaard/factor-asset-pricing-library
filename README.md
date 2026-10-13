# Factor Asset Pricing Library

A Python library and notebook sequence for academically trained students and
researchers interested in applied factor investing and empirical asset pricing.

Traded factors are both investments and asset-pricing benchmarks. The notebooks
explain how to construct their payoffs, estimate exposures and abnormal returns,
and assess what they contribute to portfolio opportunities. Each method is
followed by an application using prepared empirical data.

The Python package provides reusable calculations. Companion projects prepare
the empirical data, which are described in the [data guide](data/README.md).

## Constructing Tradable Factors

These notebooks follow the construction of an investment from measured firm characteristics to portfolio holdings and traded factor payoffs.

| Notebook | What it shows |
|---|---|
| [01 — Firm Characteristics](notebooks/01_firm_characteristics.ipynb) | Explains measurement and information timing, then computes Fama–French characteristics from observed firm records and examines their coverage and distributions. |
| [02 — Characteristic Portfolio Formation](notebooks/02_portfolio_formation.ipynb) | Explains formation, sorting, and weighting, then compares independent and conditional portfolio assignments and historical characteristic-portfolio returns. |
| [03 — Tradable Factors](notebooks/03_factor_construction.ipynb) | Defines market and long–short factor payoffs, then explains the Fama–French positions and examines their prepared return histories. |

## Evaluating Factors and Asset Pricing Models

These notebooks examine what factors explain and contribute, connecting return exposures and pricing errors to portfolio opportunities and model evaluation.

| Notebook | What it shows |
|---|---|
| [04 — Factor Spanning Tests](notebooks/04_time_series_factor_regressions.ipynb) | Tests whether characteristic factors add return beyond market exposure using CAPM regressions, residual diagnostics, and Newey–West inference. |
| [05 — Cross-Sectional Asset Pricing](notebooks/05_cross_sectional_asset_pricing.ipynb) | Uses two-pass Fama–MacBeth estimation to assess compensation for market beta across 25 Size × B/M portfolios and examine cross-sectional pricing errors. |
| [06 — Mean–Variance Portfolio Theory](notebooks/06_mean_variance_portfolio_theory.ipynb) | Develops efficient frontiers and tangency portfolios, then compares the supplied three-factor subset with FF5 using estimated opportunities and signed factor exposures. |
| [07 — Asset-Pricing Model Tests](notebooks/07_asset_pricing_model_evaluation.ipynb) | Compares CAPM, the supplied three-factor subset, and FF5 on test portfolios using alpha, GRS, and the estimated Sharpe expansion beyond the factors. |

## Applications and Empirical Finance Research

These notebooks apply the foundations to research questions about stock and factor momentum and changing factor exposure through time.

| Notebook | What it shows |
|---|---|
| [08 — Momentum](notebooks/08_momentum_in_asset_pricing.ipynb) | Constructs stock and factor momentum strategies and tests their incremental returns and ability to explain momentum-portfolio returns. |
| [09 — Volatility-Managed Factors](notebooks/09_volatility_managed_factors.ipynb) | Examines lagged inverse-variance factor scaling through managed-return spanning tests, Sharpe comparisons, and momentum downside outcomes. |

Read 01–07 in order for the foundations, then 08–09 for applications. The
sequence assumes familiarity with basic statistics, regression, and matrix
notation.

## Installation

Python 3.10 or newer is required. From a terminal:

```bash
git clone https://github.com/jacobkorsgaard/factor-asset-pricing-library.git
cd factor-asset-pricing-library
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[notebook,test]"
python -m ipykernel install --user --name factor-asset-pricing --display-name "Factor Asset Pricing"
jupyter lab
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

For Python use, import from `factor_asset_pricing`. To install only the core
package, use `python -m pip install -e .`. To run the automated tests, use
`python -m pytest -q`.

## Running the notebooks

Saved tables and figures can be read without running the code. To reproduce an
application, configure the prepared empirical inputs using the
[data guide](data/README.md) before starting Jupyter. Installing the package
does not download those inputs.

Open a notebook, select the **Factor Asset Pricing** kernel, restart it, and run
all cells from top to bottom. You can start Jupyter from the repository root or
the `notebooks/` directory. Each notebook loads its own inputs and runs
independently of earlier notebooks.

## Using the Python library

You can import the functions directly in your own scripts or notebooks. The
links below open their implementations and docstrings, which describe the
arguments and outputs. The corresponding notebooks explain the methods and
show empirical applications.

| Task | Module and useful functions | Notebook |
|---|---|---|
| Measure firm characteristics | [characteristics](src/factor_asset_pricing/characteristics.py): `market_equity`, `book_equity`, `operating_profitability`, `investment` | 01 |
| Assign holdings and calculate portfolio returns | [sorts](src/factor_asset_pricing/sorts.py): `assign_portfolios`, `assign_annual_portfolios`, `portfolio_returns` | 02 |
| Construct traded factor payoffs | [factors](src/factor_asset_pricing/factors.py): `long_short_factor`, `market_excess_return`, `fama_french_five_factors` | 03 |
| Estimate exposures, alpha, and pricing tests | [asset_pricing_tests](src/factor_asset_pricing/asset_pricing_tests.py): `time_series_regression`, `two_pass_fama_macbeth`, `grs_test`, `performance_summary` | 04, 05, 07 |
| Calculate portfolio opportunities | [mean_variance](src/factor_asset_pricing/mean_variance.py): `global_minimum_variance`, `efficient_frontier`, `tangency_portfolio` | 06 |
| Construct momentum strategies | [momentum](src/factor_asset_pricing/momentum.py): `momentum_signal`, `stock_momentum`, `factor_momentum` | 08 |
| Scale exposure using lagged realized variance | [volatility_management](src/factor_asset_pricing/volatility_management.py): `aggregate_realized_variance`, `volatility_managed_return` | 09 |

For return regressions, supply a pandas Series for one asset and a DataFrame
with one column per factor, indexed by matching dates. Use simple decimal
returns (`0.01` means 1%) at the same frequency. Subtract the matching risk-free
return from a funded asset's total return once. Traded factor excess payoffs
already require no further subtraction. The regression aligns dates and drops
incomplete rows, so check the resulting sample size.

### Example: estimate an asset's market exposure and alpha

This self-contained example uses explicitly simulated monthly returns to
demonstrate the API. Replace them with your observed, date-aligned returns for
an empirical analysis.

```python
import numpy as np
import pandas as pd
from factor_asset_pricing.asset_pricing_tests import time_series_regression

rng = np.random.default_rng(42)
dates = pd.date_range("2020-01-01", periods=60, freq="MS")
market = pd.Series(rng.normal(0.005, 0.04, 60), index=dates, name="MKT")
asset_excess = pd.Series(
    0.001 + 1.2 * market.to_numpy() + rng.normal(0, 0.015, 60),
    index=dates,
    name="asset",
)

fit = time_series_regression(
    asset_excess, market.to_frame(), cov_type="HAC", hac_lags=3
)
print(f"Monthly alpha: {100 * fit.params['const']:.3f}%")
print(f"Market beta: {fit.params['MKT']:.3f}")
print(f"Alpha t-statistic: {fit.tvalues['const']:.2f}")
print(f"Observations: {int(fit.nobs)}")
```

`const` is the estimated monthly alpha relative to this market benchmark.
`MKT` is the market beta. HAC inference allows heteroskedasticity and serial
dependence with the chosen three-month lag window. These simulated estimates
demonstrate usage and provide no evidence of an investment opportunity.

Sorting functions instead use firm-level panels with identifier, date,
characteristic, and return columns. Specify your column names and information
timing explicitly. Portfolio optimization functions use expected-return vectors
and covariance matrices in the same asset order and frequency. See the linked
docstrings and notebooks for each function's particular requirements.

## License

The package remains at version **1.0.0**. Source code and original documentation
use the [MIT License](LICENSE). Third-party data retain their providers' terms.
No licensed empirical observations are distributed in this repository.
