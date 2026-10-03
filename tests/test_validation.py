import numpy as np
import pandas as pd

from factor_asset_pricing.validation import (
    validate_factor_returns, validate_portfolios, validate_return_series,
)


def test_return_validation_reports_level_loading_and_fit():
    dates = pd.date_range("2000-01-31", periods=60, freq="ME")
    reference = pd.Series(np.linspace(-.05, .05, len(dates)), index=dates)
    constructed = .01 + 1.2 * reference
    result = validate_return_series(constructed, reference, hac_lags=3)
    assert np.isclose(result["alpha"], .01)
    assert np.isclose(result["loading"], 1.2)
    assert np.isclose(result["correlation"], 1)
    assert np.isclose(result["adjusted_r_squared"], 1)


def test_grouped_portfolio_validation_uses_matching_keys():
    dates = pd.date_range("2000-01-31", periods=30, freq="ME")
    reference = pd.DataFrame(
        [{"date": date, "portfolio": p, "benchmark": .01 * p + i / 1000}
         for i, date in enumerate(dates) for p in [1, 2]]
    )
    constructed = reference.rename(columns={"benchmark": "ret"}).copy()
    result = validate_portfolios(
        constructed, reference, portfolio_cols="portfolio", reference_col="benchmark", hac_lags=2
    )
    assert set(result.portfolio) == {1, 2}
    assert np.allclose(result.mean_difference, 0)
    assert np.allclose(result.correlation, 1)


def test_factor_panel_validation_applies_same_comparison_to_each_factor():
    dates = pd.date_range("2000-01-31", periods=40, freq="ME")
    reference = pd.DataFrame(
        {"MKT": np.linspace(-.04, .05, 40), "HML": np.linspace(.03, -.02, 40)},
        index=dates,
    )
    constructed = reference * 1.1 + .001
    result = validate_factor_returns(constructed, reference, hac_lags=2)
    assert set(result.index) == {"MKT", "HML"}
    assert np.allclose(result.loading, 1.1)
    assert np.allclose(result.alpha, .001)
