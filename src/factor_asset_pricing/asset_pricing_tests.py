"""Classical time-series asset-pricing tests."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


# =============================================================================
# 1. Time-series factor regressions
# =============================================================================
def time_series_regression(
    asset_returns: pd.Series,
    factor_returns: pd.DataFrame,
    *,
    cov_type: str = "OLS",
    hac_lags: int = 12,
):
    """Estimate an excess-return factor regression with an intercept.

    Returns the fitted statsmodels result. ``cov_type`` accepts ``'OLS'`` or
    ``'HAC'``/``'Newey-West'``; parameter estimates are identical and only
    inference changes.
    """
    name = asset_returns.name or "asset"
    sample = pd.concat([asset_returns.rename(name), factor_returns], axis=1).dropna()
    if sample.empty:
        raise ValueError("no complete observations")
    model = sm.OLS(sample[name], sm.add_constant(sample[factor_returns.columns], has_constant="add"))
    key = cov_type.lower().replace("_", "-")
    if key == "ols":
        return model.fit()
    if key in {"hac", "newey-west", "neweywest"}:
        return model.fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags, "use_correction": True})
    raise ValueError("cov_type must be 'OLS', 'HAC', or 'Newey-West'")


def factor_regressions(
    asset_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
    *,
    cov_type: str = "OLS",
    hac_lags: int = 12,
) -> pd.DataFrame:
    """Run factor regressions for several assets and report alpha, betas, and R2."""
    rows = []
    for asset in asset_returns:
        fit = time_series_regression(
            asset_returns[asset], factor_returns, cov_type=cov_type, hac_lags=hac_lags
        )
        row = {
            "asset": asset, "alpha": fit.params["const"], "alpha_se": fit.bse["const"],
            "alpha_t": fit.tvalues["const"], "alpha_pvalue": fit.pvalues["const"],
            "r_squared": fit.rsquared, "nobs": int(fit.nobs),
        }
        for factor in factor_returns:
            row[f"beta_{factor}"] = fit.params[factor]
            row[f"beta_{factor}_se"] = fit.bse[factor]
            row[f"beta_{factor}_t"] = fit.tvalues[factor]
        rows.append(row)
    return pd.DataFrame(rows).set_index("asset")


# =============================================================================
# 2. Joint alpha and spanning tests
# =============================================================================
def grs_test(asset_returns: pd.DataFrame, factor_returns: pd.DataFrame) -> dict[str, float]:
    """Gibbons--Ross--Shanken test that all time-series alphas equal zero.

    The conventional finite-sample statistic assumes iid multivariate-normal
    residuals and requires T > N + K.
    """
    sample = pd.concat({"assets": asset_returns, "factors": factor_returns}, axis=1).dropna()
    assets = sample["assets"].to_numpy()
    factors = sample["factors"].to_numpy()
    t, n = assets.shape
    k = factors.shape[1]
    if t <= n + k:
        raise ValueError("GRS requires T > N + K")
    x = np.column_stack([np.ones(t), factors])
    coefficients = np.linalg.lstsq(x, assets, rcond=None)[0]
    alpha = coefficients[0]
    residuals = assets - x @ coefficients
    residual_cov = residuals.T @ residuals / (t - k - 1)
    factor_mean = factors.mean(axis=0)
    factor_cov = np.cov(factors, rowvar=False, ddof=1)
    factor_cov = np.atleast_2d(factor_cov)
    numerator = alpha @ np.linalg.pinv(residual_cov) @ alpha
    denominator = 1 + factor_mean @ np.linalg.pinv(factor_cov) @ factor_mean
    statistic = ((t - n - k) / n) * numerator / denominator
    return {
        "statistic": float(statistic), "pvalue": float(stats.f.sf(statistic, n, t - n - k)),
        "df1": n, "df2": t - n - k, "nobs": t,
    }


def spanning_regression(
    candidate_return: pd.Series,
    spanning_returns: pd.DataFrame,
    *,
    cov_type: str = "HAC",
    hac_lags: int = 12,
):
    """Regress a candidate factor/strategy on a spanning factor set."""
    return time_series_regression(
        candidate_return, spanning_returns, cov_type=cov_type, hac_lags=hac_lags
    )


# =============================================================================
# 3. Sharpe ratios and investment opportunities
# =============================================================================
def sharpe_ratio(
    returns: pd.Series | pd.DataFrame,
    *,
    periods_per_year: int = 12,
) -> float | pd.Series:
    """Annualized arithmetic Sharpe ratio for excess returns."""
    return returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year)


def maximum_sharpe_ratio(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 12,
) -> dict:
    """Unconstrained ex-post maximum Sharpe ratio and sum-to-one weights."""
    clean = returns.dropna()
    mean = clean.mean().to_numpy()
    covariance = clean.cov().to_numpy()
    raw = np.linalg.pinv(covariance) @ mean
    total = raw.sum()
    weights = raw / total if not np.isclose(total, 0) else raw / np.abs(raw).sum()
    portfolio = clean @ weights
    return {
        "sharpe": float(sharpe_ratio(portfolio, periods_per_year=periods_per_year)),
        "weights": pd.Series(weights, index=clean.columns),
    }


def compare_maximum_sharpe(
    benchmark_returns: pd.DataFrame,
    candidate_returns: pd.DataFrame | pd.Series,
    *,
    periods_per_year: int = 12,
) -> dict:
    """Compare maximum Sharpe ratios before and after adding candidates."""
    candidate = candidate_returns.to_frame() if isinstance(candidate_returns, pd.Series) else candidate_returns
    combined = pd.concat([benchmark_returns, candidate], axis=1).dropna()
    before = maximum_sharpe_ratio(combined[benchmark_returns.columns], periods_per_year=periods_per_year)
    after = maximum_sharpe_ratio(combined, periods_per_year=periods_per_year)
    return {"benchmark": before, "augmented": after, "difference": after["sharpe"] - before["sharpe"]}
