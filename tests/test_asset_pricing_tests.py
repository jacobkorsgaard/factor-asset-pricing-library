import numpy as np
import pandas as pd

from factor_asset_pricing.asset_pricing_tests import factor_regressions, grs_test, spanning_regression


def test_time_series_regression_recovers_parameters_with_hac():
    rng = np.random.default_rng(2)
    factors = pd.DataFrame(rng.normal(size=(120, 2)), columns=["mkt", "smb"])
    assets = pd.DataFrame({"a": .01 + factors.mkt*1.2 - factors.smb*.3 + rng.normal(scale=.01, size=120)})
    result = factor_regressions(assets, factors, cov_type="HAC", hac_lags=4)
    assert np.isclose(result.loc["a", "alpha"], .01, atol=.003)
    assert np.isclose(result.loc["a", "beta_mkt"], 1.2, atol=.02)
    fit = spanning_regression(assets.a, factors)
    assert fit.rsquared > .99


def test_grs_returns_valid_f_statistic():
    rng = np.random.default_rng(4)
    factors = pd.DataFrame(rng.normal(size=(100, 2)), columns=["f1", "f2"])
    assets = pd.DataFrame(rng.normal(size=(100, 3)), columns=list("abc")) + factors.f1.to_numpy()[:, None]
    result = grs_test(assets, factors)
    assert result["statistic"] >= 0
    assert 0 <= result["pvalue"] <= 1

