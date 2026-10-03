import numpy as np
import pandas as pd

from factor_asset_pricing.asset_pricing_tests import (
    factor_regressions, fama_macbeth_regression, grs_test, performance_summary, pricing_error_summary,
    spanning_regression, two_pass_fama_macbeth,
)


def test_performance_summary_reports_hac_mean_and_drawdown():
    dates = pd.date_range("2000-01-31", periods=24, freq="ME")
    returns = pd.Series([.01] * 12 + [-.02] + [.01] * 11, index=dates, name="strategy")
    result = performance_summary(returns, hac_lags=3)
    assert result.loc["strategy", "nobs"] == 24
    assert result.loc["strategy", "maximum_drawdown"] < 0
    assert np.isfinite(result.loc["strategy", "mean_tstat"])


def test_time_series_regression_recovers_parameters_with_hac():
    rng = np.random.default_rng(2)
    factors = pd.DataFrame(rng.normal(size=(120, 2)), columns=["mkt", "smb"])
    assets = pd.DataFrame({"a": .01 + factors.mkt*1.2 - factors.smb*.3 + rng.normal(scale=.01, size=120)})
    result = factor_regressions(assets, factors, cov_type="HAC", hac_lags=4)
    assert np.isclose(result.loc["a", "alpha"], .01, atol=.003)
    assert np.isclose(result.loc["a", "beta_mkt"], 1.2, atol=.02)
    assert result.loc["a", "adjusted_r_squared"] > .99
    fit = spanning_regression(assets.a, factors)
    assert fit.rsquared > .99


def test_grs_returns_valid_f_statistic():
    rng = np.random.default_rng(4)
    factors = pd.DataFrame(rng.normal(size=(100, 2)), columns=["f1", "f2"])
    assets = pd.DataFrame(rng.normal(size=(100, 3)), columns=list("abc")) + factors.f1.to_numpy()[:, None]
    result = grs_test(assets, factors)
    assert result["statistic"] >= 0
    assert 0 <= result["pvalue"] <= 1


def test_grs_accepts_nullable_numeric_dtypes():
    rng = np.random.default_rng(9)
    factors = pd.DataFrame(
        {"f": pd.Series(rng.normal(size=60), dtype="Float64")}
    )
    assets = pd.DataFrame(
        {
            "a": pd.Series(.8 * factors["f"] + rng.normal(scale=.2, size=60), dtype="Float64"),
            "b": pd.Series(-.3 * factors["f"] + rng.normal(scale=.2, size=60), dtype="Float64"),
        }
    )
    result = grs_test(assets, factors)
    assert np.isfinite(result["statistic"])
    assert 0 <= result["pvalue"] <= 1


def test_pricing_error_summary():
    results = pd.DataFrame({"alpha": [-.01, .02, .03]})
    summary = pricing_error_summary(results)
    assert np.isclose(summary["mean_absolute_alpha"], .02)
    assert np.isclose(summary["root_mean_squared_alpha"], np.sqrt((.01**2 + .02**2 + .03**2) / 3))


def test_fama_macbeth_recovers_cross_sectional_premia():
    assets = [f"a{i}" for i in range(6)]
    exposures = pd.DataFrame({"beta": np.linspace(.5, 1.5, 6)}, index=assets)
    dates = pd.date_range("2000-01-31", periods=30, freq="ME")
    premia = np.linspace(.01, .03, len(dates))
    returns = pd.DataFrame(
        .002 + premia[:, None] * exposures.beta.to_numpy()[None, :],
        index=dates, columns=assets,
    )
    result = fama_macbeth_regression(returns, exposures, hac_lags=3)
    assert np.isclose(result["summary"].loc["constant", "estimate"], .002)
    assert np.isclose(result["summary"].loc["beta", "estimate"], premia.mean())


def test_two_pass_fama_macbeth_estimates_betas_then_cross_sections():
    dates = pd.date_range("2000-01-31", periods=40, freq="ME")
    factor = pd.DataFrame({"factor": np.linspace(-.04, .06, len(dates))}, index=dates)
    true_betas = pd.Series({f"a{i}": beta for i, beta in enumerate([.5, .8, 1.1, 1.4])})
    returns = pd.DataFrame(
        factor.factor.to_numpy()[:, None] * true_betas.to_numpy()[None, :],
        index=dates, columns=true_betas.index,
    )
    result = two_pass_fama_macbeth(returns, factor, hac_lags=3, add_constant=False)
    assert np.allclose(result["betas"]["factor"], true_betas)
    assert np.allclose(result["risk_premia"]["factor"], factor.factor)
