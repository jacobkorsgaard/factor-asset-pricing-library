"""Classical time-series asset-pricing tests."""

from __future__ import annotations

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
    sample = pd.concat([asset_returns, factor_returns], axis=1).dropna()
    if sample.empty:
        raise ValueError("no complete observations")
    model = sm.OLS(sample.iloc[:, 0], sm.add_constant(sample.iloc[:, 1:], has_constant="add"))
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
            "r_squared": fit.rsquared, "adjusted_r_squared": fit.rsquared_adj,
            "nobs": int(fit.nobs),
        }
        for factor in factor_returns:
            row[f"beta_{factor}"] = fit.params[factor]
            row[f"beta_{factor}_se"] = fit.bse[factor]
            row[f"beta_{factor}_t"] = fit.tvalues[factor]
        rows.append(row)
    return pd.DataFrame(rows).set_index("asset")


def pricing_error_summary(
    regression_results: pd.DataFrame,
    *,
    alpha_col: str = "alpha",
) -> pd.Series:
    """Summarize the cross-section of time-series pricing errors."""
    alpha = regression_results[alpha_col].dropna().astype(float)
    if alpha.empty:
        raise ValueError("no pricing errors are available")
    return pd.Series(
        {
            "n_assets": len(alpha),
            "mean_alpha": alpha.mean(),
            "mean_absolute_alpha": alpha.abs().mean(),
            "root_mean_squared_alpha": np.sqrt(np.mean(alpha**2)),
            "maximum_absolute_alpha": alpha.abs().max(),
        }
    )


# =============================================================================
# 2. Fama--MacBeth cross-sectional regressions
# =============================================================================
def estimate_factor_betas(
    asset_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Estimate full-sample time-series factor betas for each asset."""
    rows = []
    for asset in asset_returns:
        fit = time_series_regression(asset_returns[asset], factor_returns, cov_type="OLS")
        rows.append(pd.Series(fit.params.drop("const"), name=asset))
    return pd.DataFrame(rows).reindex(columns=factor_returns.columns)


def fama_macbeth_regression(
    asset_returns: pd.DataFrame,
    exposures: pd.DataFrame,
    *,
    hac_lags: int = 12,
    add_constant: bool = True,
) -> dict[str, pd.DataFrame]:
    """Estimate period-by-period cross-sectional risk premia.

    ``asset_returns`` is a date-by-asset return panel. ``exposures`` is an
    asset-by-exposure matrix containing fixed estimated betas or characteristics.
    Inference applies Newey--West/HAC standard errors to each time series of
    cross-sectional coefficient estimates.
    """
    assets = asset_returns.columns.intersection(exposures.index, sort=False)
    if len(assets) == 0:
        raise ValueError("asset_returns and exposures contain no common assets")
    x_all = exposures.loc[assets].astype(float)
    names = (["constant"] if add_constant else []) + list(x_all.columns)
    estimates = []
    dates = []
    for date, returns in asset_returns[assets].iterrows():
        valid = returns.notna() & x_all.notna().all(axis=1)
        x = x_all.loc[valid].to_numpy()
        if add_constant:
            x = np.column_stack([np.ones(valid.sum()), x])
        if valid.sum() <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
            continue
        estimates.append(np.linalg.lstsq(x, returns.loc[valid].to_numpy(dtype=float), rcond=None)[0])
        dates.append(date)
    if not estimates:
        raise ValueError("no cross section has enough assets to estimate the model")
    risk_premia = pd.DataFrame(estimates, index=pd.Index(dates, name=asset_returns.index.name), columns=names)

    rows = []
    for name in risk_premia:
        series = risk_premia[name].dropna()
        model = sm.OLS(series, np.ones((len(series), 1))).fit(
            cov_type="HAC",
            cov_kwds={"maxlags": min(hac_lags, len(series) - 1), "use_correction": True},
        )
        rows.append(
            {
                "parameter": name,
                "estimate": float(np.asarray(model.params)[0]),
                "standard_error": float(np.asarray(model.bse)[0]),
                "t_statistic": float(np.asarray(model.tvalues)[0]),
                "p_value": float(np.asarray(model.pvalues)[0]),
                "n_periods": len(series),
            }
        )
    return {"risk_premia": risk_premia, "summary": pd.DataFrame(rows).set_index("parameter")}


def two_pass_fama_macbeth(
    asset_returns: pd.DataFrame,
    factor_returns: pd.DataFrame,
    *,
    hac_lags: int = 12,
    add_constant: bool = True,
) -> dict[str, pd.DataFrame]:
    """Estimate factor betas, then run Fama--MacBeth cross-sectional regressions."""
    common_dates = asset_returns.index.intersection(factor_returns.index, sort=False)
    aligned_assets = asset_returns.loc[common_dates]
    aligned_factors = factor_returns.loc[common_dates]
    betas = estimate_factor_betas(aligned_assets, aligned_factors)
    result = fama_macbeth_regression(
        aligned_assets, betas, hac_lags=hac_lags, add_constant=add_constant
    )
    return {"betas": betas, **result}


# =============================================================================
# 3. Joint alpha and spanning tests
# =============================================================================
def grs_test(asset_returns: pd.DataFrame, factor_returns: pd.DataFrame) -> dict[str, float]:
    """Gibbons--Ross--Shanken test that all time-series alphas equal zero.

    The conventional finite-sample statistic assumes iid multivariate-normal
    residuals, full-rank factor and residual covariance matrices, and T > N + K.
    With S = E'E/(T-K-1) and Omega = (F-Fbar)'(F-Fbar)/(T-1),
    GRS = T(T-N-K)/(N(T-K-1)) * (alpha'S^-1 alpha) /
    (1 + T/(T-1) * Fbar'Omega^-1 Fbar).
    """
    sample = pd.concat({"assets": asset_returns, "factors": factor_returns}, axis=1).dropna()
    assets = sample["assets"].to_numpy(dtype=float)
    factors = sample["factors"].to_numpy(dtype=float)
    t, n = assets.shape
    k = factors.shape[1]
    if t <= n + k:
        raise ValueError("GRS requires T > N + K")
    x = np.column_stack([np.ones(t), factors])
    if np.linalg.matrix_rank(x) != k + 1:
        raise ValueError("GRS requires a full rank factor design")
    coefficients = np.linalg.lstsq(x, assets, rcond=None)[0]
    alpha = coefficients[0]
    residuals = assets - x @ coefficients
    if np.linalg.matrix_rank(residuals) != n:
        raise ValueError("GRS requires full rank residual covariance")
    residual_cov = residuals.T @ residuals / (t - k - 1)
    factor_mean = factors.mean(axis=0)
    factor_cov = np.cov(factors, rowvar=False, ddof=1)
    factor_cov = np.atleast_2d(factor_cov)
    numerator = alpha @ np.linalg.solve(residual_cov, alpha)
    denominator = 1 + (t / (t - 1)) * factor_mean @ np.linalg.solve(factor_cov, factor_mean)
    statistic = (t * (t - n - k) / (n * (t - k - 1))) * numerator / denominator
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
# 4. Sharpe ratios and investment opportunities
# =============================================================================
def sharpe_ratio(
    returns: pd.Series | pd.DataFrame,
    *,
    periods_per_year: int = 12,
) -> float | pd.Series:
    """Annualized arithmetic Sharpe ratio for excess returns."""
    return returns.mean() / returns.std(ddof=1) * np.sqrt(periods_per_year)


def performance_summary(
    returns: pd.Series | pd.DataFrame,
    *,
    periods_per_year: int = 12,
    hac_lags: int = 12,
) -> pd.DataFrame:
    """Summarize return performance with HAC inference for the mean."""
    panel = returns.to_frame() if isinstance(returns, pd.Series) else returns
    rows = []
    for name in panel:
        series = panel[name].dropna().astype(float)
        if series.empty:
            raise ValueError(f"{name}: no return observations")
        fit = sm.OLS(series.to_numpy(), np.ones((len(series), 1))).fit(
            cov_type="HAC",
            cov_kwds={
                "maxlags": min(hac_lags, len(series) - 1),
                "use_correction": True,
            },
        )
        wealth = (1 + series).cumprod()
        # W_0 = 1 precedes the first return and belongs to the running peak.
        drawdown = wealth.div(wealth.cummax().clip(lower=1)).sub(1)
        rows.append(
            {
                "asset": name,
                "mean_monthly": series.mean(),
                "mean_annualized": periods_per_year * series.mean(),
                "volatility_annualized": np.sqrt(periods_per_year) * series.std(ddof=1),
                "sharpe": sharpe_ratio(series, periods_per_year=periods_per_year),
                "mean_tstat": float(np.asarray(fit.tvalues)[0]),
                "skewness": series.skew(),
                "maximum_drawdown": drawdown.min(),
                "nobs": len(series),
                "start": series.index.min(),
                "end": series.index.max(),
            }
        )
    return pd.DataFrame(rows).set_index("asset")


def maximum_sharpe_ratio(
    returns: pd.DataFrame,
    *,
    periods_per_year: int = 12,
) -> dict:
    """Unconstrained ex-post maximum Sharpe ratio for excess returns.

    Weights follow the positive maximum-Sharpe direction. They sum to one
    when that normalization preserves its sign; otherwise they have unit gross
    exposure. They need not represent a fully invested risky portfolio.
    """
    clean = returns.dropna()
    mean = clean.mean().to_numpy()
    covariance = clean.cov().to_numpy()
    raw = np.linalg.pinv(covariance) @ mean
    total = raw.sum()
    gross = np.abs(raw).sum()
    if gross == 0:
        raise ValueError("maximum Sharpe direction is not identified")
    weights = raw / total if total > 0 and not np.isclose(total, 0) else raw / gross
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
