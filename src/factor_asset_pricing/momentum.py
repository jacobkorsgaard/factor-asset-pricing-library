"""Stock and factor momentum with explicit signal timing."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .factors import fama_french_2x3_factor, quantile_spread
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
    if pd.isna(pd.to_datetime(dates)).any() or periods.diff().dropna().le(0).any():
        raise ValueError("dates must contain unique months in increasing order")
    window_start = periods.shift(skip + lookback - 1)
    window_end = periods.shift(skip)
    # skip counts intentionally excluded observations, not permission to use
    # an older calendar window when observations are missing before month t.
    consecutive = (window_end.sub(window_start).eq(lookback - 1)
                   & periods.sub(window_end).eq(skip))
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


# =============================================================================
# 3. Value-weighted stock momentum with dated formation inputs
# =============================================================================
def _monthly_stock_panel(data, id_col, date_col):
    """Validate monthly keys and sort without depending on the input index."""
    panel = data.copy()
    panel[date_col] = pd.to_datetime(panel[date_col])
    if panel[[id_col, date_col]].isna().any().any():
        raise ValueError("security identifiers and dates must be nonmissing")
    month = panel[date_col].dt.to_period("M")
    if pd.DataFrame({"id": panel[id_col], "month": month}).duplicated().any():
        raise ValueError("security-month keys must be unique")
    return panel.sort_values([id_col, date_col]).reset_index(drop=True)


def momentum_signal_panel(
    data: pd.DataFrame, *, lookback: int = 12, skip: int = 1,
    id_col: str = "id", date_col: str = "date", return_col: str = "ret",
) -> pd.Series:
    """Vectorized monthly signals, aligned to the input rows and index.

    Equivalent to applying ``momentum_signal(..., dates=...)`` per security.
    Missing returns and calendar gaps invalidate a window; a total loss is
    allowed. Input rows need not be sorted and the input index may repeat.
    ``skip=1`` includes the last completed month; ``skip=2`` omits it.
    For a common 12–2 stock-momentum signal, use ``lookback=11, skip=2``
    to compound months t−12 through t−2.
    """
    if not isinstance(lookback, int) or not isinstance(skip, int) or lookback < 1 or skip < 1:
        raise ValueError("lookback and skip must be positive integers")
    frame = data[[id_col, date_col, return_col]].copy()
    frame["_input_row"] = np.arange(len(frame))
    frame = _monthly_stock_panel(frame, id_col, date_col)
    if not np.isfinite(frame[return_col].dropna()).all() or frame[return_col].dropna().lt(-1).any():
        raise ValueError("simple returns must be finite and cannot be below -1")
    if frame.empty:
        return pd.Series(index=data.index, dtype=float, name="momentum")
    ids = frame[id_col]
    lagged = frame.groupby(id_col)[return_col].shift(skip)

    def rolling_sum(values):
        return values.groupby(ids).rolling(lookback, min_periods=lookback).sum().droplevel(0).reindex(frame.index)

    logs = np.log1p(lagged.mask(lagged.eq(-1), 0))
    signal = np.expm1(rolling_sum(logs))
    signal = signal.mask(rolling_sum(lagged.eq(-1).astype(float)).gt(0) & signal.notna(), -1)
    months = frame[date_col].dt.to_period("M").astype("int64")
    first = months.groupby(ids).shift(skip + lookback - 1)
    last = months.groupby(ids).shift(skip)
    signal = signal.where(last.sub(first).eq(lookback - 1) & months.sub(last).eq(skip))
    result = pd.Series(signal.to_numpy(), index=frame["_input_row"]).sort_index()
    return pd.Series(result.to_numpy(), index=data.index, name="momentum")


def prepare_momentum_data(
    data: pd.DataFrame, risk_free: pd.Series, *, id_col: str = "id",
    date_col: str = "date", return_col: str = "ret",
    weight_col: str = "market_equity", exchange_col: str = "exchange",
) -> pd.DataFrame:
    """Add dated formation inputs and financed excess returns to stock records.

    Returns a sorted panel with ``lag_me``, ``lag_exchange``, ``rf`` and
    ``excess``. Market equity and exchange come from exactly the preceding
    calendar month. RF is aligned by calendar month and must cover every row.
    No stocks are filtered here: callers can impose a common signal universe
    before calculating any portfolio breakpoints.
    """
    panel = _monthly_stock_panel(data, id_col, date_col)
    if not isinstance(risk_free.index, pd.DatetimeIndex):
        raise ValueError("risk_free must have a DatetimeIndex")
    rf_months = risk_free.index.to_period("M")
    if rf_months.has_duplicates:
        raise ValueError("risk_free must contain unique months")
    month = panel[date_col].dt.to_period("M").astype("int64")
    consecutive = month.sub(month.groupby(panel[id_col]).shift(1)).eq(1)
    panel["lag_me"] = panel.groupby(id_col)[weight_col].shift(1).where(consecutive)
    panel["lag_exchange"] = panel.groupby(id_col)[exchange_col].shift(1).where(consecutive)
    panel["rf"] = panel[date_col].dt.to_period("M").map(pd.Series(risk_free.to_numpy(), index=rf_months)).astype(float)
    if not np.isfinite(panel["rf"]).all():
        raise ValueError("risk_free must cover every stock month with a finite return")
    panel["excess"] = panel[return_col] - panel["rf"]
    return panel


def _momentum_formation(data, signal_col, date_col):
    panel = data.loc[data[signal_col].notna() & np.isfinite(data["lag_me"]) & data["lag_me"].gt(0)].copy()
    if not np.isfinite(panel[signal_col]).all():
        raise ValueError("signals must be finite when present")
    panel[date_col] = pd.to_datetime(panel[date_col])
    return panel


def _momentum_labels(panel, signal_col, probabilities, date_col, reference_exchange):
    reference = panel.loc[panel["lag_exchange"].eq(reference_exchange)]
    cuts = reference.groupby(date_col)[signal_col].quantile(probabilities, interpolation="lower").unstack().reindex(columns=probabilities)
    labels = pd.Series(1, index=panel.index, dtype=float)
    for q in probabilities:
        cutoff = panel[date_col].map(cuts[q])
        labels += panel[signal_col].gt(cutoff).astype(int)
        labels = labels.where(cutoff.notna())
    return labels


def size_balanced_stock_momentum(
    data: pd.DataFrame, *, signal_col: str = "momentum", date_col: str = "date",
    reference_exchange: int = 1,
) -> pd.DataFrame:
    """Construct size-balanced 2×3 CSMOM from prepared stock observations.

    Use ``prepare_momentum_data`` first and supply a predetermined signal.
    NYSE (by default) median size and 30/70 signal cutoffs use lower observed
    quantiles and assign ties to the lower group. Cutoffs include observations
    with missing holding returns. Returns then use available-return value
    weights within cells, an ex-post data restriction. Missing extreme cells
    leave that month's combined return missing rather than changing leg size.

    Outputs are excess payoffs: ``Long only`` has exposure +1, ``Short only``
    is the signed short payoff with exposure -1, and ``Combined`` is their sum.
    """
    panel = _momentum_formation(data, signal_col, date_col)
    reference = panel.loc[panel["lag_exchange"].eq(reference_exchange)]
    size_cut = reference.groupby(date_col)["lag_me"].quantile(.5, interpolation="lower")
    mapped_size = panel[date_col].map(size_cut)
    panel["_size"] = pd.Series(np.where(panel["lag_me"].le(mapped_size), 1., 2.), index=panel.index).where(mapped_size.notna())
    panel["_momentum_group"] = _momentum_labels(panel, signal_col, [.3, .7], date_col, reference_exchange)
    cells = portfolio_returns(panel, ["_size", "_momentum_group"], return_col="excess",
                              date_col=date_col, weight_col="lag_me", lag_weights=False)
    legs = fama_french_2x3_factor(cells, size_col="_size", characteristic_col="_momentum_group",
                                date_col=date_col, name="CSMOM").set_index(date_col)
    long, short = legs["CSMOM_long"], -legs["CSMOM_short"]
    return pd.DataFrame({"Combined": long + short, "Long only": long, "Short only": short}).reindex(sorted(panel[date_col].unique())).rename_axis(date_col)


def time_series_stock_momentum(
    data: pd.DataFrame, *, signal_col: str = "momentum", date_col: str = "date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return value-weighted stock TSMOM excess payoffs and exposures.

    Takes the prepared columns from ``prepare_momentum_data`` and a supplied
    signal. For 12–2 formation, supply ``momentum_signal_panel`` with
    ``lookback=11, skip=2``; portfolio weights do not set the signal horizon.
    Absolute base weights sum to one over available holding returns; missing
    returns are excluded before normalization, an ex-post data restriction.
    Signals choose
    direction and zero signals hold cash. Neither side is rescaled separately.
    Output legs are signed excess payoffs and sum to ``Combined``. Exposure
    columns are ``long``, ``short`` (positive magnitude), ``net`` and ``gross``.
    Financed total return per unit of capital is RF plus the combined payoff.
    """
    formation = _momentum_formation(data, signal_col, date_col)
    dates = sorted(formation[date_col].unique())
    panel = formation.loc[formation["excess"].notna()].copy()
    base = panel["lag_me"] / panel.groupby(date_col)["lag_me"].transform("sum")
    signed = base * np.sign(panel[signal_col])
    long_weight, short_weight = signed.clip(lower=0), -signed.clip(upper=0)
    long = (long_weight * panel["excess"]).groupby(panel[date_col]).sum()
    short = (-short_weight * panel["excess"]).groupby(panel[date_col]).sum()
    payoffs = pd.DataFrame({"Combined": long + short, "Long only": long, "Short only": short})
    exposure = pd.DataFrame({"long": long_weight.groupby(panel[date_col]).sum(),
                             "short": short_weight.groupby(panel[date_col]).sum()})
    exposure["net"] = exposure["long"] - exposure["short"]
    exposure["gross"] = exposure["long"] + exposure["short"]
    return (payoffs.reindex(dates).rename_axis(date_col), exposure.reindex(dates).rename_axis(date_col))


def momentum_portfolio_returns(
    data: pd.DataFrame, *, signal_col: str = "momentum", n_portfolios: int = 10,
    date_col: str = "date", return_col: str = "ret", reference_exchange: int = 1,
) -> pd.DataFrame:
    """Value-weighted momentum quantile *total* returns from a prepared panel.

    Breakpoints precede current-return exclusions, use lower interpolation,
    and put ties in the lower portfolio. Empty portfolios remain missing.
    Subtract matched RF once to study excess returns of these long-only assets.
    """
    if not isinstance(n_portfolios, int) or n_portfolios < 2:
        raise ValueError("n_portfolios must be an integer of at least two")
    panel = _momentum_formation(data, signal_col, date_col)
    panel["_momentum_group"] = _momentum_labels(panel, signal_col, np.arange(1, n_portfolios) / n_portfolios,
                                               date_col, reference_exchange)
    returns = portfolio_returns(panel, "_momentum_group", return_col=return_col,
                                date_col=date_col, weight_col="lag_me", lag_weights=False)
    wide = returns.pivot(index=date_col, columns="_momentum_group", values="ret")
    return wide.reindex(index=sorted(panel[date_col].unique()), columns=range(1, n_portfolios + 1)).rename(
        columns=lambda d: f"P{d}").rename_axis(index=date_col, columns=None)
