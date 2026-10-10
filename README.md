# Factor Asset Pricing Library

A compact Python reference for researchers and students working on empirical
factor asset pricing. It combines reusable pandas-based calculations with five
notebooks explaining portfolio construction, statistical tests, and their
economic interpretation.

**Firm data → available characteristics → portfolio sorts → factors and test
assets → statistical evaluation**

The package supports reference-universe and conditional sorts, annual
formation, EW/VW returns, factor construction, OLS/HAC and GRS tests, fixed-beta
Fama–MacBeth estimation, momentum, volatility management, and unconstrained
mean–variance calculations. Data acquisition, identifier linking, and complete
empirical replication pipelines belong to the companion projects.

## Installation

Python 3.10 or newer is required. From a terminal:

```bash
git clone https://github.com/jacobkorsgaard/factor-asset-pricing-library.git
cd factor-asset-pricing-library
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.
The distribution name is `factor-asset-pricing`; imports use
`factor_asset_pricing`. Core dependencies are NumPy, pandas, SciPy, statsmodels,
and Matplotlib. The [code guide](docs/code-guide.md#complete-synthetic-example)
contains one complete executable synthetic workflow using only these dependencies.

For notebooks and tests:

```bash
python -m pip install -e ".[notebook,test]"
python -m ipykernel install --user --name factor-asset-pricing --display-name "Factor Asset Pricing"
python -m pytest -q
jupyter lab
```

Select the **Factor Asset Pricing** kernel in Jupyter; the saved notebooks name
the author's `anaconda-finance` kernel, which need not exist on your machine.
The notebook extra installs JupyterLab, ipykernel, nbconvert, and PyArrow 25 or
newer for the prepared Parquet inputs; these are not core package dependencies.

To execute a notebook without changing its saved outputs, configure its data
paths as described in the [data guide](data/README.md), then run from the
repository root:

```bash
python -m nbconvert --to notebook --execute notebooks/03_asset_pricing_model_tests.ipynb --ExecutePreprocessor.kernel_name=factor-asset-pricing --ExecutePreprocessor.timeout=1800 --output-dir=/tmp/factor-asset-pricing-executed
```

Choose another writable output directory on Windows. Notebook 01 needs no data;
Notebooks 02–05 require prepared inputs. Embedded outputs can be read without
those datasets. Installing notebook dependencies does not acquire the data.

## Five-notebook sequence

| Notebook | Purpose |
|---|---|
| [01 — From data to factors](notebooks/01_from_data_to_factors.ipynb) | Conceptual workflow, timing, signals, sorts, weights, and factor definitions |
| [02 — Factor spanning](notebooks/02_factor_spanning_tests.ipynb) | Time-series regressions, alpha, benchmark exposures, and HAC inference |
| [03 — Asset-pricing model tests](notebooks/03_asset_pricing_model_tests.ipynb) | CAPM/FF3/FF5 comparisons, test portfolios, pricing errors, and GRS |
| [04 — Momentum](notebooks/04_momentum_in_asset_pricing.ipynb) | Stock and factor momentum, calendar alignment, and spanning |
| [05 — Volatility-managed factors](notebooks/05_volatility_managed_factors.ipynb) | Lagged variance scaling, leverage, performance, and interpretation |

## Research guidance

- [Practical code guide](docs/code-guide.md): input contracts, public functions,
  and the synthetic example.
- [Methodology](docs/methodology.md): assumptions and empirical conventions.
- [Empirical data requirements](data/README.md): exact notebook schemas, paths,
  benchmark definitions, sample selection, and known provenance gaps.
- [Provenance](docs/provenance.md): companion projects and validation scope.
- [Empirical validation](docs/empirical-validation.md): numerical consequences
  of the mathematical corrections and prepared-input checksums.

The package does not verify point-in-time availability, silently repair missing
calendar observations, or model implementation costs. Research designs must
state those choices. Current stable package version: **1.0.0**.

## License

Source code and original documentation use the [MIT License](LICENSE).
Third-party datasets retain their providers' terms. No licensed empirical
observations are distributed.
