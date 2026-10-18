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


def calibrate_volatility_management(
    returns: pd.DataFrame,
    realized_variance: pd.DataFrame,
    *,
    calibration_months: int = 120,
    lag: int = 1,
) -> dict:
    """Match volatility in an initial window, then freeze each factor's scale.

    Inputs are decimal monthly factor returns and monthly realized variances
    with matching column names. The return index must be a complete, ordered
    monthly DatetimeIndex; missing early factor histories are allowed. The
    first jointly usable month starts the shared calibration window. Internal
    missing observations after that date raise rather than silently shorten
    the ten-year window or skip months in the evaluation period.

    Returns ``scale``, ``calibration_index``, ``evaluation_index``, and the
    out-of-sample ``original``, ``managed``, ``weights`` and ``lagged_measure``
    panels. Each scale matches standard deviations only in the calibration
    window; no subsequent volatility matching or refitting is performed.
    """
    if not isinstance(calibration_months, int) or calibration_months < 2:
        raise ValueError("calibration_months must be an integer of at least two")
    if not isinstance(returns.index, pd.DatetimeIndex) or returns.empty or returns.columns.empty:
        raise ValueError("returns must be a nonempty monthly date-indexed panel")
    months = returns.index.to_period("M").astype("int64")
    if returns.index.hasnans or not returns.columns.is_unique or not np.all(np.diff(months) == 1):
        raise ValueError("returns must have unique columns and consecutive months in increasing order")
    if not realized_variance.index.is_unique or not returns.columns.isin(realized_variance.columns).all():
        raise ValueError("realized_variance must have a unique index and all return columns")
    if not np.isfinite(returns.to_numpy()[returns.notna().to_numpy()]).all():
        raise ValueError("observed returns must be finite")

    constructions = {
        name: volatility_managed_return(returns[name], realized_variance[name], lag=lag, normalize=False)
        for name in returns
    }
    raw = pd.DataFrame({name: frame["managed_return"] for name, frame in constructions.items()})
    measures = pd.DataFrame({name: frame["lagged_measure"] for name, frame in constructions.items()})
    usable = returns.notna().all(axis=1) & raw.notna().all(axis=1)
    if not usable.any():
        raise ValueError("no jointly usable monthly observations")
    first = usable[usable].index[0]
    if not usable.loc[first:].all():
        raise ValueError("missing observations after the first jointly usable month")
    history = returns.index[returns.index >= first]
    if len(history) <= calibration_months:
        raise ValueError("need calibration observations and at least one out-of-sample month")
    calibration = history[:calibration_months]
    evaluation = history[calibration_months:]
    scale = returns.loc[calibration].std(ddof=1) / raw.loc[calibration].std(ddof=1)
    if not np.isfinite(scale).all() or scale.le(0).any():
        raise ValueError("calibration requires positive finite return and managed-return volatility")
    return {
        "scale": scale,
        "calibration_index": calibration,
        "evaluation_index": evaluation,
        "original": returns.loc[evaluation].copy(),
        "managed": raw.loc[evaluation].mul(scale),
        "weights": measures.loc[evaluation].rdiv(1).mul(scale),
        "lagged_measure": measures.loc[evaluation].copy(),
    }
