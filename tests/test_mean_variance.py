import numpy as np
import pytest

from factor_asset_pricing.mean_variance import (
    efficient_frontier, global_minimum_variance, one_over_n,
    portfolio_statistics, tangency_portfolio,
)


def test_tangency_rejects_negative_sum_maximum_sharpe_direction():
    with pytest.raises(ValueError, match='positive'):
        tangency_portfolio([-.05, -.1], np.diag([.04, .09]))


def test_tangency_positive_direction_matches_analytical_sharpe():
    mu = np.array([.05, .1])
    cov = np.diag([.04, .09])
    weights = tangency_portfolio(mu, cov, risk_free_rate=.02)
    expected = np.sqrt((mu - .02) @ np.linalg.solve(cov, mu - .02))
    assert weights.sum() == pytest.approx(1)
    assert portfolio_statistics(weights, mu, cov, risk_free_rate=.02)['sharpe'] == pytest.approx(expected)


def test_classical_portfolios_and_frontier():
    mu = np.array([.05, .10])
    cov = np.array([[.04, 0], [0, .09]])
    assert np.allclose(one_over_n(2), [.5, .5])
    gmv = global_minimum_variance(cov)
    assert np.isclose(gmv.sum(), 1)
    tan = tangency_portfolio(mu, cov)
    assert np.isclose(tan.sum(), 1)
    stats = portfolio_statistics(tan, mu, cov)
    assert stats["variance"] > 0
    frontier = efficient_frontier(mu, cov, n_points=5)
    assert len(frontier) == 5
    assert all(np.isclose(w.sum(), 1) for w in frontier.weights)
