"""Classical, unconstrained mean--variance portfolio calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# 1. Portfolio moments and simple allocations
# =============================================================================
def portfolio_statistics(
    weights,
    expected_returns,
    covariance,
    *,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Portfolio expected return, variance, volatility, and Sharpe ratio."""
    w = np.asarray(weights, dtype=float)
    mu = np.asarray(expected_returns, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    expected = float(w @ mu)
    variance = float(w @ cov @ w)
    volatility = float(np.sqrt(max(variance, 0)))
    sharpe = (expected - risk_free_rate) / volatility if volatility > 0 else np.nan
    return {"expected_return": expected, "variance": variance, "volatility": volatility, "sharpe": sharpe}


def one_over_n(n_assets: int) -> np.ndarray:
    """Equal weights for ``n_assets``."""
    if n_assets < 1:
        raise ValueError("n_assets must be positive")
    return np.repeat(1 / n_assets, n_assets)


# =============================================================================
# 2. Minimum-variance and tangency portfolios
# =============================================================================
def global_minimum_variance(covariance) -> np.ndarray:
    """Fully invested unconstrained global minimum-variance weights."""
    cov = np.asarray(covariance, dtype=float)
    ones = np.ones(cov.shape[0])
    direction = np.linalg.pinv(cov) @ ones
    return direction / (ones @ direction)


def tangency_portfolio(expected_returns, covariance, *, risk_free_rate: float = 0.0) -> np.ndarray:
    """Fully invested positive-Sharpe tangency weights.

    The direction Sigma^-1(mu-rf) must have a positive sum to permit
    sum-to-one normalization without reversing its maximum-Sharpe orientation.
    """
    mu = np.asarray(expected_returns, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    direction = np.linalg.pinv(cov) @ (mu - risk_free_rate)
    if np.isclose(direction.sum(), 0):
        raise ValueError("tangency direction cannot be normalized to sum to one")
    if direction.sum() < 0:
        raise ValueError("maximum-Sharpe direction requires a positive sum for fully invested weights")
    return direction / direction.sum()


# =============================================================================
# 3. Efficient frontier and visualization
# =============================================================================
def efficient_frontier(
    expected_returns,
    covariance,
    *,
    target_returns=None,
    n_points: int = 100,
) -> pd.DataFrame:
    """Analytical fully invested unconstrained minimum-variance frontier."""
    mu = np.asarray(expected_returns, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    inv = np.linalg.pinv(cov)
    ones = np.ones(len(mu))
    a = ones @ inv @ ones
    b = ones @ inv @ mu
    c = mu @ inv @ mu
    denominator = a * c - b**2
    if np.isclose(denominator, 0):
        raise ValueError("frontier is not identified")
    targets = np.linspace(mu.min(), mu.max(), n_points) if target_returns is None else np.asarray(target_returns)
    rows = []
    for target in targets:
        weights = inv @ (((c - b * target) / denominator) * ones + ((a * target - b) / denominator) * mu)
        stats = portfolio_statistics(weights, mu, cov)
        rows.append({**stats, "target_return": target, "weights": weights})
    return pd.DataFrame(rows)


def plot_efficient_frontier(
    expected_returns,
    covariance,
    *,
    risk_free_rate: float = 0.0,
    asset_names=None,
    ax=None,
):
    """Plot the risky-asset frontier and tangency portfolio; return ``(fig, ax)``."""
    frontier = efficient_frontier(expected_returns, covariance)
    weights = tangency_portfolio(expected_returns, covariance, risk_free_rate=risk_free_rate)
    tangency = portfolio_statistics(weights, expected_returns, covariance, risk_free_rate=risk_free_rate)
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    ax.plot(frontier["volatility"], frontier["expected_return"], label="Efficient frontier")
    ax.scatter(tangency["volatility"], tangency["expected_return"], marker="*", s=120, label="Tangency")
    ax.set(xlabel="Volatility", ylabel="Expected return")
    ax.legend()
    return fig, ax
