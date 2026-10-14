# Factor Asset Pricing Library

A Python library and notebook sequence for people interested in applied factor investing and empirical asset pricing.

Traded factors are both investments and asset-pricing benchmarks. The notebooks explain how to construct their payoffs, estimate exposures and abnormal returns, and assess their contribution to portfolio opportunities. Each method is followed by an application using prepared empirical data.

The Python package provides reusable calculations. The required empirical inputs are described in the [data guide](data/README.md).

## Constructing Tradable Factors

These notebooks follow the construction of an investment from measured firm characteristics to portfolio holdings and traded factor payoffs. Execution requires original licensed WRDS exports; run 00 first to prepare the local inputs for 01–03.

| Notebook | What it shows |
|---|---|
| [00 — CRSP–Compustat Data Preparation](notebooks/00_crsp_compustat_data_preparation.ipynb) | Cleans and links original WRDS exports into reproducible local inputs for firm characteristics, portfolios, and factors. |
| [01 — Firm Characteristics](notebooks/01_firm_characteristics.ipynb) | Measures Fama–French firm characteristics, accounting for information timing, coverage, and distributions. |
| [02 — Characteristic Portfolio Formation](notebooks/02_portfolio_formation.ipynb) | Constructs characteristic portfolios using alternative sorting and weighting methods. |
| [03 — Tradable Factors](notebooks/03_factor_construction.ipynb) | Constructs market and long–short factor payoffs and examines Fama–French factor returns. |

## Evaluating Factors and Asset Pricing Models

These notebooks investigate whether a tradable factor generates abnormal returns, captures priced sources of risk, expands the mean–variance efficient frontier, and improves the pricing performance of existing asset-pricing models.

| Notebook | What it shows |
|---|---|
| [04 — Factor Spanning Tests](notebooks/04_time_series_factor_regressions.ipynb) | Evaluates factor spanning using CAPM regressions, residual diagnostics, and Newey–West inference. |
| [05 — Cross-Sectional Asset Pricing](notebooks/05_cross_sectional_asset_pricing.ipynb) | Estimates compensation for market beta using Fama–MacBeth regressions and examines pricing errors. |
| [06 — Mean–Variance Portfolio Theory](notebooks/06_mean_variance_portfolio_theory.ipynb) | Constructs efficient frontiers and tangency portfolios and compares factor investment opportunities. |
| [07 — Asset-Pricing Model Tests](notebooks/07_asset_pricing_model_evaluation.ipynb) | Evaluates CAPM, three-factor, and five-factor models using portfolio alphas, GRS tests, and Sharpe ratios. |

## Applications and Empirical Finance Research

These notebooks extend beyond the foundations of factor asset pricing to explore selected research questions and contemporary stylized facts from the empirical asset-pricing literature. Notebooks 04–09 use publicly available Kenneth French data, downloaded automatically when missing.

| Notebook | What it shows |
|---|---|
| [08 — Momentum](notebooks/08_momentum_in_asset_pricing.ipynb) | Constructs stock and factor momentum strategies and evaluates their incremental returns and explanatory power. |
| [09 — Volatility-Managed Factors](notebooks/09_volatility_managed_factors.ipynb) | Examines volatility-managed factors using spanning tests, Sharpe comparisons, and momentum downside outcomes. |

## Installation and Setup

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

On Windows PowerShell, activate the environment using `.venv\Scripts\Activate.ps1`.

To reproduce the empirical applications, configure the required inputs following the [data guide](data/README.md). Empirical data are not downloaded during installation.

Open a notebook, select the **Factor Asset Pricing** kernel, and run its cells from top to bottom. Each notebook runs independently, and saved figures and tables can be inspected without executing the code.

To install only the Python package, use `python -m pip install -e .`. Run the automated tests using `python -m pytest -q`.

## Using the Python Library

The package provides reusable functions that can be imported directly into Python scripts or notebooks. The implementations and docstrings describe their inputs and outputs, while the accompanying notebooks explain the underlying methods.

| Task | Module and useful functions | Notebook |
|---|---|---|
| Read WRDS exports and local inputs | [wrds_data](src/factor_asset_pricing/wrds_data.py): `read_wrds_source`, `load_prepared_data` | 00–03 |
| Clean and link CRSP–Compustat observations | [data_preparation](src/factor_asset_pricing/data_preparation.py): `clean_crsp`, `clean_compustat`, `clean_ccm`, `link_crsp_compustat` | 00 |
| Measure firm characteristics | [characteristics](src/factor_asset_pricing/characteristics.py): `market_equity`, `book_equity`, `operating_profitability`, `investment` | 01 |
| Form portfolios and calculate returns | [sorts](src/factor_asset_pricing/sorts.py): `assign_portfolios`, `assign_annual_portfolios`, `portfolio_returns` | 02 |
| Apply annual characteristic-portfolio construction | [construction](src/factor_asset_pricing/construction.py): `characteristic_panel`, `annual_test_portfolios`, `annual_ff5_assignments` | 02, 03 |
| Construct traded factors | [factors](src/factor_asset_pricing/factors.py): `long_short_factor`, `market_excess_return`, `fama_french_five_factors` | 03 |
| Read public French factor and portfolio returns | [french_data](src/factor_asset_pricing/french_data.py): `load_french`, `sample_coverage` | 02–09 |
| Estimate exposures and conduct pricing tests | [asset_pricing_tests](src/factor_asset_pricing/asset_pricing_tests.py): `time_series_regression`, `two_pass_fama_macbeth`, `grs_test`, `performance_summary` | 04, 05, 07 |
| Optimize portfolios | [mean_variance](src/factor_asset_pricing/mean_variance.py): `global_minimum_variance`, `efficient_frontier`, `tangency_portfolio` | 06 |
| Construct momentum strategies | [momentum](src/factor_asset_pricing/momentum.py): `momentum_signal`, `stock_momentum`, `factor_momentum` | 08 |
| Construct volatility-managed factors | [volatility_management](src/factor_asset_pricing/volatility_management.py): `aggregate_realized_variance`, `volatility_managed_return` | 09 |

Functions require appropriately structured financial data. Return-based calculations use consistent frequencies and decimal returns, while portfolio formation requires correctly dated firm-level observations. Consult the linked docstrings for specific input conventions and requirements.

## License

Distributed under the [MIT License](LICENSE). Third-party data remain subject to their providers' terms. No licensed empirical observations are distributed in this repository.
