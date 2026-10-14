"""Small annual-formation recipes composing existing analytical APIs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .characteristics import fama_french_characteristics
from .data_preparation import previous_month_weights
from .sorts import assign_annual_portfolios, portfolio_returns


def characteristic_panel(panel: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    """Measure characteristics from independent annual inputs and lagged market data.

    Financial definitions are delegated to the existing characteristics API.
    Explicit current formation-history flags avoid confusing June's prior holding
    year with the year of the June decision.
    """
    data = fama_french_characteristics(panel.rename(columns={"date": "crsp_date", "mdate": "date"}), annual_data=annual)
    data["mdate"] = data["date"]
    december = data.loc[data.month.eq(12), ["permno", "year"]].copy()
    december["year"] += 1
    december["has_prior_december"] = True
    data = data.merge(december, on=["permno", "year"], how="left", validate="many_to_one")
    data["has_prior_december"] = data.has_prior_december.eq(True)
    data["formation_eligible"] = data.me.gt(0) & data.has_prior_december
    data["weight"] = previous_month_weights(data)
    return data


def annual_ff5_assignments(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Independent June 2×3 grids; July–June holdings and reference size median.

    The generic quantile API uses lower interpolation. For the reference FF5
    size split only, replace the lower 50% order statistic with the actual NYSE
    median, including the midpoint for an even reference count.
    """
    result = assign_annual_portfolios(data, ["me", "bm", "op", "inv"], [2, 3, 3, 3],
        id_col="permno", eligible="formation_eligible", exchange_col="exchcd",
        breakpoint_probabilities={"bm": [.3, .7], "op": [.3, .7], "inv": [.3, .7]})
    formation = result["formation"]
    medians = formation.loc[formation.exchcd.eq(1)].groupby("_formation_year").me.median()
    cut = formation._formation_year.map(medians)
    formation["me_portfolio"] = np.where(cut.notna(), np.where(formation.me.le(cut), 1., 2.), np.nan)
    labels = formation[["permno", "_formation_year", "me_portfolio"]].rename(columns={"_formation_year": "ffyear"})
    result["panel"] = result["panel"].drop(columns="me_portfolio").merge(labels, on=["permno", "ffyear"], how="left", validate="many_to_one")
    breaks = result["breakpoints"]
    size_rows = breaks.characteristic.eq("me")
    breaks.loc[size_rows, "breakpoint"] = breaks.loc[size_rows, "_formation_year"].map(medians)
    return result


def annual_test_portfolios(data: pd.DataFrame, characteristic: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Independent NYSE quintiles and lagged-VW returns, with no missing-cell fill."""
    if characteristic not in {"bm", "op", "inv"}:
        raise ValueError("characteristic must be bm, op, or inv")
    result = assign_annual_portfolios(data, ["me", characteristic], [5, 5], id_col="permno",
                                    eligible="formation_eligible", exchange_col="exchcd")
    returns = portfolio_returns(result["panel"], ["me_portfolio", f"{characteristic}_portfolio"],
        id_col="permno", return_col="retadj", weight_col="weight", lag_weights=False)
    return returns.rename(columns={"me_portfolio": "row_portfolio", f"{characteristic}_portfolio": "column_portfolio", "date": "mdate"}), result["breakpoints"]
