"""Stock and factor momentum with explicit signal timing."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .factors import quantile_spread
from .sorts import portfolio_returns


# =============================================================================
# 1. Stock-momentum signals and portfolios
# =============================================================================
def momentum_signal(
    returns: pd.Series,
    *,
    lookback: int = 12,
    skip: int = 1,
    log_returns: bool = False,
) -> pd.Series:
    """Trailing cumulative return ending ``skip`` periods before month t."""
    if lookback < 1 or skip < 0:
        raise ValueError("lookback must be positive and skip nonnegative")
    lagged = returns.shift(skip)
    if log_returns:
        return lagged.rolling(lookback, min_periods=lookback).sum()
    if (returns.dropna() <= -1).any():
        raise ValueError("simple returns must be greater than -1")
    return np.expm1(np.log1p(lagged).rolling(lookback, min_periods=lookback).sum())


def stock_momentum(
    data: pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
    holding_period: int = 1,
    n_portfolios: int = 10,
    reference="nyse",
    weighting: str = "vw",
    id_col: str = "id",
    date_col: str = "date",
    return_col: str = "ret",
    exchange_col: str = "exchange",
    weight_col: str = "market_equity",
    name: str = "MOM",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construct stock-momentum quantile portfolios and winner-minus-loser factor.

    For holding periods above one, overlapping vintage returns are averaged
    with equal vintage weights, the standard calendar-time implementation.
    """
    if holding_period < 1:
        raise ValueError("holding_period must be positive")
    panel = data.sort_values([id_col, date_col]).copy()
    panel["momentum"] = panel.groupby(id_col, observed=True)[return_col].transform(
        lambda x: momentum_signal(x, lookback=lookback, skip=skip)
    )
    # Compute the implementable weight before expanding the panel into holding
    # vintages; lagging after expansion would accidentally lag across duplicate
    # security-month rows.
    panel["_beginning_weight"] = panel.groupby(id_col, observed=True)[weight_col].shift(1)
    # Assign at formation and carry each vintage forward for its holding life.
    pieces = []
    for vintage in range(holding_period):
        formed = panel.copy()
        formed["_formation_signal"] = formed.groupby(id_col, observed=True)["momentum"].shift(vintage)
        formed["_formation_date"] = formed.groupby(id_col, observed=True)[date_col].shift(vintage)
        # Current-date cross sections use the appropriately lagged vintage signal.
        from .sorts import assign_portfolios
        formed = assign_portfolios(
            formed, "_formation_signal", n_portfolios, date_col=date_col,
            reference=reference, exchange_col=exchange_col,
        ).rename(columns={"_formation_signal_portfolio": "momentum_portfolio"})
        formed["vintage"] = vintage
        pieces.append(formed)
    assigned = pd.concat(pieces, ignore_index=True)
    vintage_returns = portfolio_returns(
        assigned, ["vintage", "momentum_portfolio"], return_col=return_col,
        date_col=date_col, weighting=weighting, weight_col="_beginning_weight",
        id_col=id_col, lag_weights=False,
    )
    portfolios = vintage_returns.groupby([date_col, "momentum_portfolio"], observed=True).agg(
        ret=("ret", "mean"), n_vintages=("vintage", "size")
    ).reset_index()
    factor = quantile_spread(
        portfolios, portfolio_col="momentum_portfolio", n_portfolios=n_portfolios,
        date_col=date_col, name=name,
    )
    return factor, portfolios


# =============================================================================
# 2. Factor momentum
# =============================================================================
def factor_momentum_positions(
    factor_returns: pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
    holding_period: int = 1,
) -> pd.DataFrame:
    """Equal-weight sign positions across factors with optional overlapping holds."""
    if lookback < 1 or skip < 1 or holding_period < 1:
        raise ValueError("lookback, skip, and holding_period must be positive")
    signal = np.sign(factor_returns.rolling(lookback, min_periods=lookback).mean().shift(skip))
    vintages = [signal.shift(v) for v in range(holding_period)]
    combined = sum(v.fillna(0) for v in vintages) / sum(v.notna().astype(int) for v in vintages).replace(0, np.nan)
    available = combined.notna() & factor_returns.notna()
    return combined.where(available).div(available.sum(axis=1).replace(0, np.nan), axis=0)


def factor_momentum(
    factor_returns: pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
    holding_period: int = 1,
    name: str = "factor_momentum",
) -> pd.Series:
    """Return the equal-weight time-series factor-momentum portfolio."""
    positions = factor_momentum_positions(
        factor_returns, lookback=lookback, skip=skip, holding_period=holding_period
    )
    result = (positions * factor_returns).sum(axis=1, min_count=1)
    result.name = name
    return result
