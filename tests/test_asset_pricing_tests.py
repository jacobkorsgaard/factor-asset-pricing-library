import numpy as np
import pandas as pd
import pytest
from scipy import stats
import statsmodels.api as sm
import ast
import json
from pathlib import Path

from factor_asset_pricing.asset_pricing_tests import (
    factor_regressions, fama_macbeth_regression, grs_test, performance_summary, pricing_error_summary,
    spanning_regression, two_pass_fama_macbeth,
    maximum_sharpe_ratio, compare_maximum_sharpe, time_series_regression,
)


def test_grs_matches_independent_divisor_t_calculation():
    rng = np.random.default_rng(1)
    factors = pd.DataFrame(rng.normal(.01, .05, (100, 2)))
    assets = pd.DataFrame(.01 + rng.normal(0, .04, (100, 3)))
    # Independent OLS fits and ML covariance normalization, rather than the
    # implementation's unbiased covariance matrices and adjusted prefactor.
    fits = [sm.OLS(assets[c], sm.add_constant(factors)).fit() for c in assets]
    alpha = np.array([fit.params.iloc[0] for fit in fits])
    errors = np.column_stack([fit.resid for fit in fits])
    sigma = errors.T @ errors / len(assets)
    centered = factors.to_numpy() - factors.mean().to_numpy()
    omega = centered.T @ centered / len(factors)
    mean = factors.mean().to_numpy()
    expected = (95 / 3) * (alpha @ np.linalg.solve(sigma, alpha)) / (
        1 + mean @ np.linalg.solve(omega, mean)
    )
    result = grs_test(assets, factors)
    assert expected == pytest.approx(10.093957706224327)
    assert result['statistic'] == pytest.approx(expected, rel=1e-12)
    assert result['pvalue'] == pytest.approx(stats.f.sf(expected, 3, 95))


def test_single_asset_grs_equals_squared_ols_alpha_t():
    rng = np.random.default_rng(19)
    factors = pd.DataFrame({'f': rng.normal(.02, .05, 35)})
    assets = pd.DataFrame({'a': .01 + .7 * factors.f + rng.normal(0, .03, 35)})
    fit = time_series_regression(assets.a, factors)
    assert grs_test(assets, factors)['statistic'] == pytest.approx(fit.tvalues['const'] ** 2)


def test_grs_rejects_redundant_factors_and_assets():
    rng = np.random.default_rng(23)
    factors = pd.DataFrame({'f': rng.normal(size=40)})
    assets = pd.DataFrame(rng.normal(size=(40, 2)))
    with pytest.raises(ValueError, match='full rank'):
        grs_test(assets, factors.assign(duplicate=factors.f))
    with pytest.raises(ValueError, match='full rank'):
        grs_test(assets.assign(duplicate=assets[0]), factors)


def test_drawdown_includes_initial_wealth():
    returns = pd.Series([-.2, .1, .1], name='strategy')
    assert performance_summary(returns, hac_lags=0).loc['strategy', 'maximum_drawdown'] == pytest.approx(-.2)


def test_regression_allows_matching_asset_and_factor_names():
    factors = pd.DataFrame({'f': [-.02, .01, .03, -.01, .04]})
    candidate = (.005 + 2 * factors.f).rename('f')
    fit = time_series_regression(candidate, factors)
    assert fit.params['const'] == pytest.approx(.005)
    assert fit.params['f'] == pytest.approx(2)


def test_maximum_sharpe_preserves_negative_and_zero_sum_directions():
    deviations = np.array([-.03, -.01, .01, .03])
    for means in [(-.05, -.05), (.05, -.05), (.05, .05)]:
        returns = pd.DataFrame({'a': means[0] + deviations,
                                'b': means[1] + deviations[[1, 3, 0, 2]]})
        result = maximum_sharpe_ratio(returns)
        mean = returns.mean().to_numpy()
        expected = np.sqrt(12 * mean @ np.linalg.solve(returns.cov(), mean))
        assert result['sharpe'] == pytest.approx(expected)
        if means[0] < 0:
            assert result['weights'].sum() < 0
        elif means[1] < 0:
            assert result['weights'].sum() == pytest.approx(0, abs=1e-12)
        else:
            assert result['weights'].sum() == pytest.approx(1)


def test_adding_candidate_cannot_reduce_unconstrained_maximum_sharpe():
    returns = pd.DataFrame({'a': [-.08, -.06, -.04, -.02],
                            'b': [-.03, -.01, -.02, -.04]})
    result = compare_maximum_sharpe(returns[['a']], returns.b)
    assert result['difference'] >= -1e-12


def test_notebook_downside_statistics_include_initial_wealth():
    path = Path(__file__).resolve().parents[1] / 'notebooks/05_volatility_managed_factors.ipynb'
    notebook = json.loads(path.read_text())
    source = next(''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code' and ''.join(cell['source']).startswith('def downside_statistics'))
    function = ast.parse(source).body[0]
    namespace = {'sharpe_ratio': lambda series: 0}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    result = namespace['downside_statistics'](pd.Series([-.2, .1, .1]))
    assert result['Maximum drawdown (%)'] == pytest.approx(-20)


def test_notebook_long_only_sharpe_uses_risk_free_returns():
    from factor_asset_pricing.asset_pricing_tests import sharpe_ratio

    path = Path(__file__).resolve().parents[1] / 'notebooks/04_momentum_in_asset_pricing.ipynb'
    notebook = json.loads(path.read_text())
    source = next(''.join(cell['source']) for cell in notebook['cells']
                  if cell['cell_type'] == 'code' and 'stock_performance = ' in ''.join(cell['source']))
    statements = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            'stock_performance' in ast.unparse(target) for target in node.targets
        ):
            statements.append(node)
    panel = pd.DataFrame({'Winners': [.02, .03, -.01, .04],
                          'Losers': [.01, -.02, .02, .01],
                          'WML': [.01, .05, -.03, .03]})
    rf = pd.Series(.005, index=panel.index)
    namespace = {'stock_strategy_returns': panel, 'risk_free': rf,
                 'performance_summary': performance_summary, 'sharpe_ratio': sharpe_ratio}
    exec(compile(ast.Module(body=statements, type_ignores=[]), str(path), 'exec'), namespace)
    result = namespace['stock_performance']
    assert result.loc['Winners', 'sharpe'] == pytest.approx(sharpe_ratio(panel.Winners - rf))
    assert result.loc['Losers', 'sharpe'] == pytest.approx(sharpe_ratio(panel.Losers - rf))
    assert result.loc['WML', 'sharpe'] == pytest.approx(sharpe_ratio(panel.WML))
    assert result.loc['Winners', 'mean_monthly'] == pytest.approx(panel.Winners.mean())


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
