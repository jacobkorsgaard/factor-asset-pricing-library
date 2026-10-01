"""Characteristic-sorted test assets built on :mod:`sorts`."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .sorts import sort_portfolios


# =============================================================================
# 1. Sorted test-asset returns
# =============================================================================
def characteristic_portfolios(
    data: pd.DataFrame,
    characteristics: str | Sequence[str],
    n_portfolios: int | Sequence[int],
    **sort_kwargs,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construct univariate, bivariate, or three-way test portfolios."""
    return sort_portfolios(data, characteristics, n_portfolios, **sort_kwargs)


def univariate_portfolios(data, characteristic, n_portfolios, **kwargs):
    return characteristic_portfolios(data, characteristic, n_portfolios, **kwargs)


def bivariate_portfolios(data, characteristics, n_portfolios, **kwargs):
    if len(characteristics) != 2:
        raise ValueError("bivariate portfolios require two characteristics")
    return characteristic_portfolios(data, characteristics, n_portfolios, **kwargs)


def multivariate_portfolios(data, characteristics, n_portfolios, **kwargs):
    if len(characteristics) != 3:
        raise ValueError("multivariate portfolios require three characteristics")
    return characteristic_portfolios(data, characteristics, n_portfolios, **kwargs)


# =============================================================================
# 2. Portfolio characteristics and excess returns
# =============================================================================
def portfolio_average_characteristics(
    assigned_data: pd.DataFrame,
    portfolio_cols: str | Sequence[str],
    characteristics: str | Sequence[str],
    *,
    date_col: str = "date",
    weighting: str = "ew",
    weight_col: str = "market_equity",
) -> pd.DataFrame:
    """Compute EW or contemporaneously VW portfolio-average characteristics."""
    portfolios = [portfolio_cols] if isinstance(portfolio_cols, str) else list(portfolio_cols)
    chars = [characteristics] if isinstance(characteristics, str) else list(characteristics)
    keys = [date_col, *portfolios]
    sample = assigned_data.dropna(subset=keys).copy()
    if weighting == "ew":
        return sample.groupby(keys, observed=True)[chars].mean().reset_index()
    if weighting != "vw":
        raise ValueError("weighting must be 'ew' or 'vw'")
    sample = sample.loc[sample[weight_col].gt(0) & sample[weight_col].notna()]
    rows = []
    for key, group in sample.groupby(keys, observed=True):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(keys, key))
        for char in chars:
            valid = group[char].notna()
            row[char] = group.loc[valid, char].mul(group.loc[valid, weight_col]).sum() / group.loc[valid, weight_col].sum()
        rows.append(row)
    return pd.DataFrame(rows)


def to_excess_returns(
    returns: pd.DataFrame,
    risk_free: pd.Series | pd.DataFrame,
    *,
    date_col: str = "date",
    return_cols: Sequence[str] | None = None,
    risk_free_col: str = "rf",
) -> pd.DataFrame:
    """Subtract a date-aligned risk-free rate from test-asset returns."""
    out = returns.copy()
    if isinstance(risk_free, pd.Series):
        rf = risk_free.rename(risk_free_col)
        if date_col in out and rf.index.name == date_col:
            out = out.join(rf, on=date_col)
        else:
            out[risk_free_col] = rf.reindex(out.index)
    else:
        out = out.merge(risk_free[[date_col, risk_free_col]], on=date_col, how="left")
    columns = list(return_cols) if return_cols is not None else ["ret"]
    for col in columns:
        out[col] = out[col] - out[risk_free_col]
    return out
