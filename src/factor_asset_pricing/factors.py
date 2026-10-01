"""Factor construction from portfolio or security returns."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .sorts import portfolio_returns


# =============================================================================
# 1. Generic long-short factors
# =============================================================================
def long_short_factor(
    portfolio_data: pd.DataFrame,
    *,
    portfolio_col: str,
    high,
    low,
    return_col: str = "ret",
    date_col: str = "date",
    name: str = "factor",
) -> pd.DataFrame:
    """Construct a high-minus-low factor and retain its two legs.

    When the input contains several cells for each high or low label, the
    function equally averages their returns within each leg before taking the
    spread.
    """
    sample = portfolio_data.loc[portfolio_data[portfolio_col].isin([low, high])].copy()
    legs = sample.groupby([date_col, portfolio_col], observed=True)[return_col].mean().unstack(portfolio_col)
    for label in (high, low):
        if label not in legs:
            legs[label] = np.nan
    result = pd.DataFrame({
        f"{name}_long": legs[high],
        f"{name}_short": legs[low],
        name: legs[high] - legs[low],
    }).reset_index()
    return result


def quantile_spread(
    portfolio_data: pd.DataFrame,
    *,
    portfolio_col: str,
    n_portfolios: int | None = None,
    return_col: str = "ret",
    date_col: str = "date",
    name: str = "factor",
) -> pd.DataFrame:
    """Construct the highest-minus-lowest quantile spread."""
    high = n_portfolios or portfolio_data[portfolio_col].max()
    return long_short_factor(
        portfolio_data, portfolio_col=portfolio_col, high=high, low=1,
        return_col=return_col, date_col=date_col, name=name,
    )


# =============================================================================
# 2. Fama--French-style factor construction
# =============================================================================
def fama_french_2x3_factor(
    cells: pd.DataFrame,
    *,
    size_col: str,
    characteristic_col: str,
    small=1,
    big=2,
    low=1,
    high=3,
    return_col: str = "ret",
    date_col: str = "date",
    name: str = "HML",
) -> pd.DataFrame:
    """Construct FF-style characteristic and size factors from 2x3 cells.

    The characteristic factor is the average of high cells across size minus
    the average of low cells.  The size factor is the mean of the three small
    cells minus the mean of the three big cells.  Separate legs are returned.
    """
    wide = cells.pivot_table(index=date_col, columns=[size_col, characteristic_col], values=return_col)
    def cell(a, b):
        return wide[(a, b)] if (a, b) in wide else pd.Series(np.nan, index=wide.index)
    long_leg = (cell(small, high) + cell(big, high)) / 2
    short_leg = (cell(small, low) + cell(big, low)) / 2
    small_leg = pd.concat([cell(small, q) for q in (low, 2, high)], axis=1).mean(axis=1, skipna=False)
    big_leg = pd.concat([cell(big, q) for q in (low, 2, high)], axis=1).mean(axis=1, skipna=False)
    return pd.DataFrame({
        f"{name}_long": long_leg, f"{name}_short": short_leg, name: long_leg - short_leg,
        "SMB_long": small_leg, "SMB_short": big_leg, "SMB": small_leg - big_leg,
    }).reset_index()


def factor_from_assignments(
    data: pd.DataFrame,
    *,
    portfolio_col: str,
    high,
    low,
    weighting: str = "vw",
    return_col: str = "ret",
    date_col: str = "date",
    weight_col: str = "market_equity",
    id_col: str = "id",
    lag_weights: bool = True,
    name: str = "factor",
) -> pd.DataFrame:
    """Construct an EW or VW long-short factor directly from assignments."""
    returns = portfolio_returns(
        data, portfolio_col, return_col=return_col, date_col=date_col,
        weighting=weighting, weight_col=weight_col, id_col=id_col,
        lag_weights=lag_weights,
    )
    return long_short_factor(
        returns, portfolio_col=portfolio_col, high=high, low=low,
        return_col="ret", date_col=date_col, name=name,
    )


# =============================================================================
# 3. Market excess return
# =============================================================================
def market_excess_return(
    data: pd.DataFrame,
    *,
    return_col: str = "ret",
    risk_free_col: str = "rf",
    date_col: str = "date",
    weighting: str = "vw",
    weight_col: str = "market_equity",
    id_col: str = "id",
    lag_weights: bool = True,
    name: str = "MKT",
) -> pd.DataFrame:
    """Construct the market return minus the risk-free rate."""
    sample = data.copy()
    sample["_market"] = 1
    market = portfolio_returns(
        sample, "_market", return_col=return_col, date_col=date_col,
        weighting=weighting, weight_col=weight_col, id_col=id_col,
        lag_weights=lag_weights,
    )[[date_col, "ret"]]
    rf = sample.groupby(date_col, observed=True)[risk_free_col].first().rename(risk_free_col)
    market = market.join(rf, on=date_col)
    market[name] = market["ret"] - market[risk_free_col]
    return market[[date_col, name, risk_free_col]]
