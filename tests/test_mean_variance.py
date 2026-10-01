import numpy as np

from factor_asset_pricing.mean_variance import (
    efficient_frontier, global_minimum_variance, one_over_n,
    portfolio_statistics, tangency_portfolio,
)


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
