"""Lagged realized-volatility management without forecast-model machinery."""

from __future__ import annotations

import numpy as np
import pandas as pd


# =============================================================================
# 1. Realized variance and volatility
# =============================================================================
def realized_variance(returns: pd.Series, *, demean: bool = True, min_obs: int = 2) -> float:
    """Realized variance: the within-period sum of squared daily returns."""
    values = pd.Series(returns).dropna()
    if len(values) < min_obs:
        return np.nan
    if demean:
        values = values - values.mean()
    return float(values.pow(2).sum())


def realized_volatility(returns: pd.Series, *, demean: bool = True, min_obs: int = 2) -> float:
    """Square root of realized variance."""
    variance = realized_variance(returns, demean=demean, min_obs=min_obs)
    return float(np.sqrt(variance)) if np.isfinite(variance) else np.nan


def aggregate_realized_variance(
    daily_returns: pd.DataFrame,
    *,
    return_cols: list[str] | None = None,
    date_col: str = "date",
    period: str = "M",
    demean: bool = True,
    min_obs: int = 2,
) -> pd.DataFrame:
    """Aggregate daily return columns to period realized variances."""
    data = daily_returns.copy()
    cols = return_cols or [c for c in data.select_dtypes(include="number") if c != date_col]
    data[date_col] = pd.to_datetime(data[date_col])
    data["period"] = data[date_col].dt.to_period(period)
    result = data.groupby("period", observed=True)[cols].agg(
        lambda x: realized_variance(x, demean=demean, min_obs=min_obs)
    )
    return result.add_prefix("rv_").reset_index()


# =============================================================================
# 2. Lagged volatility management
# =============================================================================
def volatility_managed_return(
    returns: pd.Series,
    realized_measure: pd.Series,
    *,
    scaling: str = "inverse_variance",
    lag: int = 1,
    normalize: bool = True,
) -> pd.DataFrame:
    """Scale returns by lagged variance or volatility.

    With normalization, one positive full-sample constant matches the managed
    return's sample volatility to the original return's volatility.  This is
    the convention in the reference volatility-management project and is an
    ex-post comparison device, not a real-time target.
    """
    if scaling not in {"inverse_variance", "inverse_volatility"}:
        raise ValueError("scaling must be 'inverse_variance' or 'inverse_volatility'")
    if lag < 1:
        raise ValueError("lag must be positive")
    measure = pd.Series(realized_measure).reindex(returns.index).shift(lag)
    denominator = measure if scaling == "inverse_variance" else np.sqrt(measure)
    if (denominator.dropna() <= 0).any():
        raise ValueError("realized measure must be positive where used")
    unscaled = returns / denominator
    valid = returns.notna() & unscaled.notna()
    constant = 1.0
    if normalize:
        constant = returns.loc[valid].std(ddof=1) / unscaled.loc[valid].std(ddof=1)
    weight = constant / denominator
    return pd.DataFrame({
        "return": returns, "lagged_measure": measure, "weight": weight,
        "managed_return": weight * returns,
    })
