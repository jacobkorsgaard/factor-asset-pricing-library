"""Stock and factor momentum with explicit signal timing."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .factors import quantile_spread
from .sorts import assign_portfolios, portfolio_returns


# =============================================================================
# 1. Stock-momentum signals and portfolios
# =============================================================================
def momentum_signal(
    returns: pd.Series,
    *,
    lookback: int = 12,
    skip: int = 1,
    log_returns: bool = False,
    dates: pd.Series | pd.Index | None = None,
) -> pd.Series:
    """Trailing cumulative return ending the requested periods before month t.

    When dates are supplied, signals spanning a gap in a monthly return history
    are set to missing instead of treating nonconsecutive observations as
    adjacent months.
    """
    if lookback < 1 or skip < 0:
        raise ValueError("lookback must be positive and skip nonnegative")
    lagged = returns.shift(skip)
    if log_returns:
        signal = lagged.rolling(lookback, min_periods=lookback).sum()
    elif (returns.dropna() < -1).any():
        raise ValueError("simple returns cannot be below -1")
    else:
        signal = lagged.add(1).rolling(lookback, min_periods=lookback).apply(
            np.prod, raw=True
        ).sub(1)
    if dates is None:
        return signal
    periods = pd.Series(pd.to_datetime(dates), index=returns.index).dt.to_period("M").astype("int64")
    window_start = periods.shift(skip + lookback - 1)
    window_end = periods.shift(skip)
    consecutive = window_end.sub(window_start).eq(lookback - 1)
    return signal.where(consecutive)


def conditional_future_returns(
    returns: pd.Series | pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
) -> pd.DataFrame:
    """Average current returns following negative or positive trailing returns."""
    panel = returns.to_frame() if isinstance(returns, pd.Series) else returns
    rows = []
    for name in panel:
        signal = momentum_signal(panel[name], lookback=lookback, skip=skip)
        sample = pd.concat([panel[name].rename("return"), signal.rename("signal")], axis=1).dropna()
        negative = sample.loc[sample["signal"].lt(0), "return"]
        positive = sample.loc[sample["signal"].gt(0), "return"]
        rows.append(
            {
                "asset": name,
                "after_negative": negative.mean(),
                "after_positive": positive.mean(),
                "difference": positive.mean() - negative.mean(),
                "n_negative": len(negative),
                "n_positive": len(positive),
            }
        )
    return pd.DataFrame(rows).set_index("asset")


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
    signals = []
    for _, group in panel.groupby(id_col, observed=True, sort=False):
        signals.append(
            momentum_signal(
                group[return_col], lookback=lookback, skip=skip, dates=group[date_col]
            )
        )
    panel["momentum"] = pd.concat(signals).reindex(panel.index)
    # Compute the implementable weight before expanding the panel into holding
    # vintages; lagging after expansion would accidentally lag across duplicate
    # security-month rows.
    panel["_beginning_weight"] = panel.groupby(id_col, observed=True)[weight_col].shift(1)
    dates = pd.to_datetime(panel[date_col]).dt.to_period("M").astype("int64")
    prior_dates = dates.groupby(panel[id_col], observed=True).shift(1)
    panel.loc[dates.sub(prior_dates).ne(1), "_beginning_weight"] = np.nan
    # Assign once in each formation-month cross section, then carry that fixed
    # label forward for the life of each vintage.
    panel = assign_portfolios(
        panel,
        "momentum",
        n_portfolios,
        date_col=date_col,
        reference=reference,
        exchange_col=exchange_col,
    ).rename(columns={"momentum_portfolio": "_formed_portfolio"})
    pieces = []
    for vintage in range(holding_period):
        formed = panel.copy()
        formed["momentum_portfolio"] = formed.groupby(id_col, observed=True)[
            "_formed_portfolio"
        ].shift(vintage)
        formed["_formation_date"] = formed.groupby(id_col, observed=True)[date_col].shift(vintage)
        current_period = pd.to_datetime(formed[date_col]).dt.to_period("M").astype("int64")
        formation_period = pd.to_datetime(formed["_formation_date"]).dt.to_period("M").astype("int64")
        formed.loc[current_period.sub(formation_period).ne(vintage), "momentum_portfolio"] = np.nan
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
    trailing = factor_returns.apply(
        lambda series: momentum_signal(series, lookback=lookback, skip=skip)
    )
    signal = np.sign(trailing)
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


def cross_sectional_momentum_positions(
    returns: pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
) -> pd.DataFrame:
    """Median-split cross-sectional momentum weights with unit gross exposure.

    Each period allocates +0.5 equally across assets above the cross-sectional
    median signal and -0.5 equally across assets below it. Median ties are not
    held. Missing signals or current returns are never treated as zero returns.
    """
    if lookback < 1 or skip < 1:
        raise ValueError("lookback and skip must be positive")
    signal = returns.apply(lambda series: momentum_signal(series, lookback=lookback, skip=skip))
    available = signal.notna() & returns.notna()
    median = signal.where(available).median(axis=1)
    long = signal.gt(median, axis=0) & available
    short = signal.lt(median, axis=0) & available
    long_count = long.sum(axis=1).replace(0, np.nan)
    short_count = short.sum(axis=1).replace(0, np.nan)
    weights = long.div(2 * long_count, axis=0) - short.div(2 * short_count, axis=0)
    valid = long_count.notna() & short_count.notna()
    return weights.where(valid, np.nan)


def cross_sectional_momentum(
    returns: pd.DataFrame,
    *,
    lookback: int = 12,
    skip: int = 1,
    name: str = "cross_sectional_momentum",
) -> pd.Series:
    """Return a median-split cross-sectional momentum strategy."""
    positions = cross_sectional_momentum_positions(
        returns, lookback=lookback, skip=skip
    )
    result = (positions * returns).sum(axis=1, min_count=1)
    result.name = name
    return result


def lagged_correlation_matrix(returns: pd.DataFrame, *, lag: int = 1) -> pd.DataFrame:
    """Correlation of current asset returns with lagged returns of every asset."""
    if lag < 1:
        raise ValueError("lag must be positive")
    current = returns.add_prefix("current:")
    lagged = returns.shift(lag).add_prefix("lagged:")
    correlation = pd.concat([current, lagged], axis=1).corr()
    result = correlation.loc[current.columns, lagged.columns]
    result.index = returns.columns
    result.columns = returns.columns
    return result
