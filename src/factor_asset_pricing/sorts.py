"""Portfolio sorting and return aggregation.

The functions operate on long panels.  Portfolio labels are integers starting
at one.  Values equal to a breakpoint enter the lower portfolio, matching the
Fama--French replication used as the main reference for this package.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pandas as pd


ReferenceUniverse = str | pd.Series | Callable[[pd.DataFrame], pd.Series]


# =============================================================================
# 1. Signal timing and breakpoints
# =============================================================================
def lag_characteristics(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    *,
    id_col: str = "id",
    date_col: str = "date",
    lags: int | Mapping[str, int] = 1,
    suffix: str = "_lag",
) -> pd.DataFrame:
    """Return a copy with characteristics lagged within security.

    ``lags`` may be one integer or a mapping from characteristic to lag.  Rows
    are sorted by security and date before shifting.  This is appropriate for
    monthly characteristics; annual Fama--French formation can instead be
    represented by supplying a precomputed ``formation_col`` to ``assign_portfolios``.
    """
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    out = data.sort_values([id_col, date_col]).copy()
    for char in chars:
        lag = lags[char] if isinstance(lags, Mapping) else lags
        if not isinstance(lag, int) or lag < 0:
            raise ValueError("lags must be nonnegative integers")
        out[f"{char}{suffix}{lag}"] = out.groupby(id_col, observed=True)[char].shift(lag)
    return out


def quantile_breakpoints(values: pd.Series, n_portfolios: int) -> np.ndarray:
    """Compute ``n_portfolios - 1`` empirical quantiles using lower interpolation."""
    if not isinstance(n_portfolios, int) or n_portfolios < 2:
        raise ValueError("n_portfolios must be an integer of at least two")
    clean = pd.Series(values).dropna()
    if clean.empty:
        return np.full(n_portfolios - 1, np.nan)
    probabilities = np.arange(1, n_portfolios) / n_portfolios
    return clean.quantile(probabilities, interpolation="lower").to_numpy(dtype=float)


def _reference_mask(data: pd.DataFrame, reference: ReferenceUniverse, exchange_col: str) -> pd.Series:
    if isinstance(reference, str):
        key = reference.lower()
        if key in {"all", "full", "full_universe"}:
            return pd.Series(True, index=data.index)
        if key == "nyse":
            if exchange_col not in data:
                raise KeyError(f"NYSE breakpoints require {exchange_col!r}")
            return data[exchange_col].isin([1, "N", "NYSE"])
        if reference in data.columns:
            return data[reference].fillna(False).astype(bool)
        raise ValueError("reference must be 'nyse', 'all', a boolean column, mask, or callable")
    mask = reference(data) if callable(reference) else reference
    mask = pd.Series(mask, index=data.index) if not isinstance(mask, pd.Series) else mask.reindex(data.index)
    return mask.fillna(False).astype(bool)


def _labels_from_breaks(values: pd.Series, breaks: Sequence[float]) -> pd.Series:
    breaks = np.asarray(breaks, dtype=float)
    result = pd.Series(np.nan, index=values.index, dtype=float)
    if np.isfinite(breaks).all():
        result.loc[values.notna()] = np.searchsorted(breaks, values.dropna(), side="left") + 1
    return result.astype("Int64")


# =============================================================================
# 2. Portfolio assignment
# =============================================================================
def assign_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int],
    *,
    date_col: str = "date",
    formation_col: str | None = None,
    reference: ReferenceUniverse = "nyse",
    exchange_col: str = "exchange",
    method: str = "independent",
    label_suffix: str = "_portfolio",
) -> pd.DataFrame:
    """Assign arbitrary one-, two-, or three-way quantile portfolios.

    Breakpoints are calculated separately by ``formation_col`` (or date).  In
    independent sorts every characteristic uses the same reference universe.
    In dependent/sequential sorts, later breakpoints are conditional on all
    earlier portfolio assignments. The reference rule is applied in every
    conditional cell.
    """
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    if not 1 <= len(chars) <= 3:
        raise ValueError("one to three characteristics are supported")
    counts = [n_portfolios] * len(chars) if isinstance(n_portfolios, int) else list(n_portfolios)
    if len(counts) != len(chars) or any(not isinstance(n, int) or n < 2 for n in counts):
        raise ValueError("n_portfolios must provide an integer >= 2 per characteristic")
    if method not in {"independent", "dependent", "sequential"}:
        raise ValueError("method must be 'independent' or 'dependent'/'sequential'")

    out = data.copy()
    period = formation_col or date_col
    if period not in out:
        raise KeyError(period)
    ref = _reference_mask(out, reference, exchange_col)
    prior_labels: list[str] = []

    for char, count in zip(chars, counts):
        if char not in out:
            raise KeyError(char)
        label = f"{char}{label_suffix}"
        out[label] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        conditioning = prior_labels if method in {"dependent", "sequential"} else []
        keys = [period, *conditioning]
        groups = out.groupby(keys, observed=True, dropna=False).groups
        for _, indices in groups.items():
            indices = pd.Index(indices)
            reference_values = out.loc[indices[ref.loc[indices]], char]
            breaks = quantile_breakpoints(reference_values, count)
            out.loc[indices, label] = _labels_from_breaks(out.loc[indices, char], breaks).to_numpy()
        prior_labels.append(label)
    return out


# =============================================================================
# 3. Portfolio returns and combined sorting interface
# =============================================================================
def portfolio_returns(
    data: pd.DataFrame,
    portfolio_cols: str | Sequence[str],
    *,
    return_col: str = "ret",
    date_col: str = "date",
    weighting: str = "vw",
    weight_col: str = "market_equity",
    id_col: str = "id",
    lag_weights: bool = True,
) -> pd.DataFrame:
    """Aggregate equal- or value-weighted returns for assigned portfolios.

    By default value weights are the security's preceding observation of
    ``weight_col``, which prevents using end-of-return-period market equity.
    Set ``lag_weights=False`` when the supplied column already contains the
    implementable beginning-of-period weight.
    """
    portfolios = [portfolio_cols] if isinstance(portfolio_cols, str) else list(portfolio_cols)
    if weighting not in {"ew", "vw"}:
        raise ValueError("weighting must be 'ew' or 'vw'")
    out = data.copy()
    keys = [date_col, *portfolios]
    required = [*keys, return_col]
    if weighting == "vw":
        required.extend([id_col, weight_col] if lag_weights else [weight_col])
    sample = out[required].copy()
    if weighting == "vw":
        if lag_weights:
            sample = sample.sort_values([id_col, date_col])
            sample["_weight"] = sample.groupby(id_col, observed=True)[weight_col].shift(1)
        else:
            sample["_weight"] = sample[weight_col]
        sample = sample.loc[np.isfinite(sample["_weight"]) & sample["_weight"].gt(0)]
    sample = sample.dropna(subset=keys + [return_col])
    grouped = sample.groupby(keys, observed=True)
    if weighting == "ew":
        result = grouped[return_col].agg(ret="mean", n_firms="size").reset_index()
    else:
        sample["_weighted_ret"] = sample[return_col] * sample["_weight"]
        result = grouped.agg(
            weighted_sum=("_weighted_ret", "sum"), weight_sum=("_weight", "sum"), n_firms=(return_col, "size")
        ).reset_index()
        result["ret"] = result["weighted_sum"] / result["weight_sum"]
        result = result[[*keys, "ret", "n_firms"]]
    return result.sort_values(keys).reset_index(drop=True)


def sort_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int],
    *,
    return_col: str = "ret",
    date_col: str = "date",
    formation_col: str | None = None,
    reference: ReferenceUniverse = "nyse",
    exchange_col: str = "exchange",
    method: str = "independent",
    weighting: str = "vw",
    weight_col: str = "market_equity",
    id_col: str = "id",
    lag_weights: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign portfolios and return ``(returns, assigned_panel)``."""
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    assigned = assign_portfolios(
        data, chars, n_portfolios, date_col=date_col, formation_col=formation_col,
        reference=reference, exchange_col=exchange_col, method=method,
    )
    labels = [f"{char}_portfolio" for char in chars]
    returns = portfolio_returns(
        assigned, labels, return_col=return_col, date_col=date_col, weighting=weighting,
        weight_col=weight_col, id_col=id_col, lag_weights=lag_weights,
    )
    return returns, assigned
