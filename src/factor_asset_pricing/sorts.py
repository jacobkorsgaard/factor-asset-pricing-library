"""Portfolio sorting, annual assignment, and return aggregation.

Portfolio labels are integers starting at one. Values equal to a breakpoint
enter the lower portfolio, matching the Fama--French replication convention.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pandas as pd


ReferenceUniverse = str | pd.Series | Callable[[pd.DataFrame], pd.Series]


# =============================================================================
# 1. Signal timing and breakpoint specifications
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
    """Return a copy with characteristics lagged within security."""
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    out = data.sort_values([id_col, date_col]).copy()
    for char in chars:
        lag = lags[char] if isinstance(lags, Mapping) else lags
        if not isinstance(lag, int) or lag < 0:
            raise ValueError("lags must be nonnegative integers")
        out[f"{char}{suffix}{lag}"] = out.groupby(id_col, observed=True)[char].shift(lag)
    return out


def quantile_breakpoints(
    values: pd.Series,
    n_portfolios: int | None = None,
    *,
    probabilities: Sequence[float] | None = None,
) -> np.ndarray:
    """Compute lower-interpolation quantiles.

    Supply either an equal number of portfolios or explicit probabilities such
    as ``[0.3, 0.7]`` for a Fama--French 30/40/30 split.
    """
    if probabilities is None:
        if not isinstance(n_portfolios, int) or n_portfolios < 2:
            raise ValueError("n_portfolios must be an integer of at least two")
        probabilities = np.arange(1, n_portfolios) / n_portfolios
    probabilities = np.asarray(probabilities, dtype=float)
    if (
        probabilities.ndim != 1
        or len(probabilities) == 0
        or np.any(probabilities <= 0)
        or np.any(probabilities >= 1)
        or np.any(np.diff(probabilities) <= 0)
    ):
        raise ValueError("probabilities must be strictly increasing and between zero and one")
    clean = pd.Series(values).dropna()
    if clean.empty:
        return np.full(len(probabilities), np.nan)
    return clean.quantile(probabilities, interpolation="lower").to_numpy(dtype=float)


def _portfolio_specifications(
    characteristics: list[str],
    n_portfolios: int | Sequence[int] | None,
    breakpoint_probabilities: Mapping[str, Sequence[float]] | None,
) -> dict[str, np.ndarray]:
    if n_portfolios is None:
        counts = [None] * len(characteristics)
    elif isinstance(n_portfolios, int):
        counts = [n_portfolios] * len(characteristics)
    else:
        counts = list(n_portfolios)
        if len(counts) != len(characteristics):
            raise ValueError("n_portfolios must provide one value per characteristic")

    explicit = breakpoint_probabilities or {}
    unknown = set(explicit) - set(characteristics)
    if unknown:
        raise ValueError(f"probabilities supplied for unknown characteristics: {sorted(unknown)}")

    specifications = {}
    for char, count in zip(characteristics, counts):
        if char in explicit:
            probabilities = np.asarray(explicit[char], dtype=float)
            quantile_breakpoints(pd.Series(dtype=float), probabilities=probabilities)
        else:
            if not isinstance(count, int) or count < 2:
                raise ValueError(
                    f"{char}: provide n_portfolios >= 2 or explicit breakpoint probabilities"
                )
            probabilities = np.arange(1, count) / count
        specifications[char] = probabilities
    return specifications


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
def _assign_with_breakpoints(
    data: pd.DataFrame,
    characteristics: list[str],
    specifications: Mapping[str, np.ndarray],
    *,
    period: str,
    reference_mask: pd.Series,
    method: str,
    conditional_on: Mapping[str, Sequence[str]] | None,
    label_suffix: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = data.copy()
    prior: list[str] = []
    breakpoint_rows = []
    if conditional_on is not None:
        unknown = set(conditional_on) - set(characteristics)
        if unknown:
            raise ValueError(f"conditioning supplied for unknown characteristics: {sorted(unknown)}")

    for char in characteristics:
        if char not in out:
            raise KeyError(char)
        label = f"{char}{label_suffix}"
        out[label] = pd.Series(pd.NA, index=out.index, dtype="Int64")
        if conditional_on is None:
            parents = prior if method in {"dependent", "sequential"} else []
        else:
            parents = list(conditional_on.get(char, []))
            unavailable = [parent for parent in parents if parent not in prior]
            if unavailable:
                raise ValueError(
                    f"{char}: conditioning characteristics must be assigned earlier: {unavailable}"
                )
        conditioning_labels = [f"{parent}{label_suffix}" for parent in parents]
        keys = [period, *conditioning_labels]

        grouping = keys[0] if len(keys) == 1 else keys
        for group_key, indices in out.groupby(grouping, observed=True, dropna=False).groups.items():
            indices = pd.Index(indices)
            probabilities = specifications[char]
            breaks = quantile_breakpoints(
                out.loc[indices[reference_mask.loc[indices]], char], probabilities=probabilities
            )
            out.loc[indices, label] = _labels_from_breaks(out.loc[indices, char], breaks).to_numpy()
            group_values = group_key if isinstance(group_key, tuple) else (group_key,)
            base = dict(zip(keys, group_values))
            for number, (probability, value) in enumerate(zip(probabilities, breaks), start=1):
                breakpoint_rows.append(
                    {
                        **base,
                        "characteristic": char,
                        "breakpoint_number": number,
                        "probability": probability,
                        "breakpoint": value,
                    }
                )
        prior.append(char)
    return out, pd.DataFrame(breakpoint_rows)


def assign_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int] | None = None,
    *,
    date_col: str = "date",
    formation_col: str | None = None,
    reference: ReferenceUniverse = "nyse",
    exchange_col: str = "exchange",
    method: str = "independent",
    breakpoint_probabilities: Mapping[str, Sequence[float]] | None = None,
    conditional_on: Mapping[str, Sequence[str]] | None = None,
    label_suffix: str = "_portfolio",
) -> pd.DataFrame:
    """Assign one-, two-, or three-way quantile portfolios.

    Independent sorts use unconditional breakpoints. Sequential sorts condition
    each later characteristic on every earlier assignment. ``conditional_on``
    can instead identify the exact earlier characteristics defining each
    breakpoint sample.
    """
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    if not chars:
        raise ValueError("at least one characteristic is required")
    if method not in {"independent", "dependent", "sequential"}:
        raise ValueError("method must be 'independent' or 'dependent'/'sequential'")
    period = formation_col or date_col
    if period not in data:
        raise KeyError(period)
    specifications = _portfolio_specifications(chars, n_portfolios, breakpoint_probabilities)
    assigned, _ = _assign_with_breakpoints(
        data,
        chars,
        specifications,
        period=period,
        reference_mask=_reference_mask(data, reference, exchange_col),
        method=method,
        conditional_on=conditional_on,
        label_suffix=label_suffix,
    )
    return assigned


def _eligibility_mask(data: pd.DataFrame, eligible) -> pd.Series:
    if eligible is None:
        return pd.Series(True, index=data.index)
    if isinstance(eligible, str):
        return data[[eligible]].fillna(False).astype(bool).all(axis=1)
    if isinstance(eligible, Sequence) and not isinstance(eligible, pd.Series):
        columns = list(eligible)
        if columns and all(isinstance(column, str) for column in columns):
            return data[columns].fillna(False).astype(bool).all(axis=1)
    mask = eligible(data) if callable(eligible) else eligible
    mask = pd.Series(mask, index=data.index) if not isinstance(mask, pd.Series) else mask.reindex(data.index)
    return mask.fillna(False).astype(bool)


def assign_annual_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int] | None = None,
    *,
    id_col: str = "id",
    date_col: str = "date",
    formation_month: int = 6,
    holding_start_month: int = 7,
    eligible=None,
    reference: ReferenceUniverse = "nyse",
    exchange_col: str = "exchange",
    method: str = "independent",
    breakpoint_probabilities: Mapping[str, Sequence[float]] | None = None,
    conditional_on: Mapping[str, Sequence[str]] | None = None,
    label_suffix: str = "_portfolio",
) -> dict[str, pd.DataFrame]:
    """Form annual portfolios and carry assignments through holding months.

    For the default June/July convention, formation-year t assignments are
    applied from July t through June t+1. ``eligible`` may be boolean columns,
    a mask, or a callable evaluated on the panel.
    """
    if formation_month not in range(1, 13) or holding_start_month not in range(1, 13):
        raise ValueError("formation_month and holding_start_month must be between 1 and 12")
    if formation_month == holding_start_month:
        raise ValueError("holding_start_month must begin after the formation month")
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    if not chars:
        raise ValueError("at least one characteristic is required")
    if method not in {"independent", "dependent", "sequential"}:
        raise ValueError("method must be 'independent' or 'dependent'/'sequential'")
    specifications = _portfolio_specifications(chars, n_portfolios, breakpoint_probabilities)

    panel = data.copy()
    dates = pd.to_datetime(panel[date_col])
    holding_year = np.where(
        dates.dt.month >= holding_start_month, dates.dt.year, dates.dt.year - 1
    )
    panel["_holding_year"] = holding_year - int(formation_month > holding_start_month)
    formation = panel.loc[dates.dt.month.eq(formation_month) & _eligibility_mask(panel, eligible)].copy()
    formation["_formation_year"] = pd.to_datetime(formation[date_col]).dt.year
    if formation.duplicated([id_col, "_formation_year"]).any():
        raise ValueError("formation sample contains multiple observations per security and year")

    assigned_formation, breakpoints = _assign_with_breakpoints(
        formation,
        chars,
        specifications,
        period="_formation_year",
        reference_mask=_reference_mask(formation, reference, exchange_col),
        method=method,
        conditional_on=conditional_on,
        label_suffix=label_suffix,
    )
    labels = [f"{char}{label_suffix}" for char in chars]
    assignments = assigned_formation[[id_col, "_formation_year", *labels]].rename(
        columns={"_formation_year": "_holding_year"}
    )
    assigned_panel = panel.merge(assignments, on=[id_col, "_holding_year"], how="left")
    return {
        "panel": assigned_panel.drop(columns="_holding_year").sort_values([id_col, date_col]).reset_index(drop=True),
        "formation": assigned_formation.drop(columns="_holding_year").reset_index(drop=True),
        "breakpoints": breakpoints.reset_index(drop=True),
    }


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
    """Aggregate equal- or value-weighted returns for assigned portfolios."""
    portfolios = [portfolio_cols] if isinstance(portfolio_cols, str) else list(portfolio_cols)
    if weighting not in {"ew", "vw"}:
        raise ValueError("weighting must be 'ew' or 'vw'")
    keys = [date_col, *portfolios]
    required = [*keys, return_col]
    if weighting == "vw":
        required.extend([id_col, weight_col] if lag_weights else [weight_col])
    sample = data[required].copy()
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
            weighted_sum=("_weighted_ret", "sum"),
            weight_sum=("_weight", "sum"),
            n_firms=(return_col, "size"),
        ).reset_index()
        result["ret"] = result["weighted_sum"] / result["weight_sum"]
        result = result[[*keys, "ret", "n_firms"]]
    return result.sort_values(keys).reset_index(drop=True)


def sort_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int] | None = None,
    *,
    return_col: str = "ret",
    date_col: str = "date",
    formation_col: str | None = None,
    reference: ReferenceUniverse = "nyse",
    exchange_col: str = "exchange",
    method: str = "independent",
    breakpoint_probabilities: Mapping[str, Sequence[float]] | None = None,
    conditional_on: Mapping[str, Sequence[str]] | None = None,
    weighting: str = "vw",
    weight_col: str = "market_equity",
    id_col: str = "id",
    lag_weights: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Assign portfolios and return ``(returns, assigned_panel)``."""
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    assigned = assign_portfolios(
        data,
        chars,
        n_portfolios,
        date_col=date_col,
        formation_col=formation_col,
        reference=reference,
        exchange_col=exchange_col,
        method=method,
        breakpoint_probabilities=breakpoint_probabilities,
        conditional_on=conditional_on,
    )
    labels = [f"{char}_portfolio" for char in chars]
    returns = portfolio_returns(
        assigned,
        labels,
        return_col=return_col,
        date_col=date_col,
        weighting=weighting,
        weight_col=weight_col,
        id_col=id_col,
        lag_weights=lag_weights,
    )
    return returns, assigned
