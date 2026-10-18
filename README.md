# Factor Asset Pricing Library

This repository brings together some of my work on tradable factors within a single project, allowing me to collect, organize, and further develop my implementations of methods from the factor asset pricing literature. At the same time, it is intended to serve as a Python library with reusable code and a sequence of educational notebooks for anyone interested in applied factor investing and empirical asset pricing.

From a practical perspective, traded factors serve two main purposes. First and foremost, they represent investable strategies, while also providing benchmarks for measuring risk exposures and evaluating investment performance. Consequently, factor asset pricing is not only of theoretical interest but also has practical applications in portfolio construction, investment evaluation, and risk management. These are the perspectives I aim to emphasize throughout this repository.

To make these methods accessible and illustrate their practical relevance, I have developed a sequence of notebooks explaining how to construct factor portfolios and their returns, estimate factor exposures and abnormal returns, and evaluate their contribution to investment opportunities. Each method is accompanied by an empirical application using prepared financial data, connecting the underlying theory to its implementation and interpretation.

## Constructing Tradable Factors

Notebooks 00–04 follow the construction of an investment from prepared data and measured firm characteristics to portfolio holdings and traded factor payoffs. Momentum in 04 applies this framework to signals based on past returns. Execution of these notebooks requires original licensed WRDS exports of CRSP and Compustat data. Run 00 first to prepare the local inputs for 01–04.

| Notebook | What it shows |
|---|---|
| [00 - CRSP–Compustat Data Preparation](notebooks/00_crsp_compustat_data_preparation.ipynb) | Cleans and links original WRDS exports into reproducible local inputs for firm characteristics, portfolios, and factors. |
| [01 - Firm Characteristics](notebooks/01_firm_characteristics.ipynb) | Measures Fama–French firm characteristics, accounting for information timing, coverage, and distributions. |
| [02 - Characteristic Portfolio Formation](notebooks/02_portfolio_formation.ipynb) | Constructs characteristic portfolios using alternative sorting and weighting methods. |
| [03 - Tradable Factors](notebooks/03_factor_construction.ipynb) | Constructs market and long–short factor payoffs and examines Fama–French factor returns. |
| [04 - Cross-Sectional and Time-Series Momentum](notebooks/04_momentum_in_asset_pricing.ipynb) | Constructs US equity momentum strategies and compares formation horizons, long and short legs, and benchmark-adjusted performance. |

## Evaluating Factors and Asset Pricing Models

Notebooks 05–08 move from constructing investments to evaluating them. They examine individual factor contributions, cross-sectional pricing, portfolio investment opportunities, and joint asset-pricing model tests. These notebooks use publicly available Kenneth French data and do not require WRDS access.

| Notebook | What it shows |
|---|---|
| [05 - Factor Spanning Tests](notebooks/05_time_series_factor_regressions.ipynb) | Evaluates whether the characteristic factors and published MOM add to the market using CAPM regressions and Newey–West inference. |
| [06 - Cross-Sectional Asset Pricing](notebooks/06_cross_sectional_asset_pricing.ipynb) | Estimates compensation for market beta using Fama–MacBeth regressions and examines pricing errors. |
| [07 - Mean–Variance Portfolio Theory](notebooks/07_mean_variance_portfolio_theory.ipynb) | Constructs efficient frontiers and tangency portfolios and compares factor investment opportunities. |
| [08 - Asset-Pricing Model Tests](notebooks/08_asset_pricing_model_evaluation.ipynb) | Evaluates CAPM, three-factor, and five-factor models using portfolio alphas, GRS tests, and Sharpe ratios. |

## Applications and Empirical Finance Research

Notebook 09 applies the preceding evaluation methods to changing factor exposure over time through volatility management. It uses publicly available Kenneth French data and does not require WRDS access.

| Notebook | What it shows |
|---|---|
| [09 - Volatility-Managed Factors](notebooks/09_volatility_managed_factors.ipynb) | Calibrates volatility management over an initial ten-year window, then compares out-of-sample Sharpe ratios, cumulative returns, and benchmark alphas. |

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

Place original WRDS exports in `data/raw/wrds/` and Kenneth French CSV or ZIP files in `data/raw/french/`. Run notebook 00 before 01–04. Select the **Factor Asset Pricing** kernel and run cells from top to bottom.

## Using the Python Library

To install only the Python package, use `python -m pip install -e .`. Run the automated tests using `python -m pytest -q`.

The package provides reusable functions that can be imported directly into Python scripts or notebooks. The implementations and docstrings describe their inputs and outputs, while the accompanying notebooks explain the underlying methods.

| Task | Module and useful functions | Notebook |
|---|---|---|
| Measure firm characteristics | [characteristics](src/factor_asset_pricing/characteristics.py): `market_equity`, `book_equity`, `operating_profitability`, `investment` | 01 |
| Form portfolios and calculate returns | [sorts](src/factor_asset_pricing/sorts.py): `assign_portfolios`, `assign_annual_portfolios`, `portfolio_returns`. [construction](src/factor_asset_pricing/construction.py) combines these with characteristic measurement for annual portfolios. | 02, 03 |
| Construct traded factors | [factors](src/factor_asset_pricing/factors.py): `long_short_factor`, `market_excess_return`, `fama_french_five_factors` | 03 |
| Construct momentum strategies | [momentum](src/factor_asset_pricing/momentum.py): `prepare_momentum_data`, `momentum_signal_panel`, `size_balanced_stock_momentum`, `time_series_stock_momentum`, `momentum_portfolio_returns` | 04 |
| Estimate exposures and conduct pricing tests | [asset_pricing_tests](src/factor_asset_pricing/asset_pricing_tests.py): `time_series_regression`, `two_pass_fama_macbeth`, `grs_test`, `performance_summary` | 05, 06, 08 |
| Optimize portfolios | [mean_variance](src/factor_asset_pricing/mean_variance.py): `global_minimum_variance`, `efficient_frontier`, `tangency_portfolio` | 07 |
| Construct volatility-managed factors | [volatility_management](src/factor_asset_pricing/volatility_management.py): `aggregate_realized_variance`, `volatility_managed_return`, `calibrate_volatility_management` | 09 |

Data preparation is supported by [wrds_data](src/factor_asset_pricing/wrds_data.py), [data_preparation](src/factor_asset_pricing/data_preparation.py), and [french_data](src/factor_asset_pricing/french_data.py). These modules read and prepare local source files. Required WRDS inputs are listed in notebook 00. The French reader reports the official download URL when a required file is missing.

Functions require appropriately structured financial data. Return-based calculations use consistent frequencies and decimal returns, while portfolio formation requires correctly dated firm-level observations. Consult the linked docstrings for specific input conventions and requirements.

## Main Textbook References

The explanations and methods in this repository draw primarily on three books that have shaped my understanding of investments and empirical asset pricing:

- **Munk, C. (2023). *Financial Markets and Investments*.** Foundations of investments, portfolio choice, and factor models.
- **Cochrane, J. H. (2005). *Asset Pricing*, revised edition.** Asset-pricing theory, regression-based tests, and their portfolio interpretation.
- **Campbell, J. Y., Lo, A. W., and MacKinlay, A. C. (1997). *The Econometrics of Financial Markets*.** Financial econometrics, return predictability, and empirical methods.

## License

Distributed under the [MIT License](LICENSE). Third-party data remain subject to their providers' terms. No licensed empirical observations are distributed in this repository.
