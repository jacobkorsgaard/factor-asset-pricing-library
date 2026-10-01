import numpy as np
import pandas as pd

from factor_asset_pricing.sorts import assign_portfolios, lag_characteristics, portfolio_returns


def panel():
    rows = []
    for month in pd.date_range("2020-01-31", periods=2, freq="ME"):
        for i in range(1, 9):
            rows.append({"date": month, "id": i, "exchange": 1 if i <= 4 else 2,
                         "x": float(i), "y": float(9-i), "z": float(i % 3),
                         "ret": i / 100, "market_equity": float(i)})
    return pd.DataFrame(rows)


def test_nyse_breakpoints_and_arbitrary_independent_sort():
    assigned = assign_portfolios(panel(), ["x", "y", "z"], [2, 4, 3], reference="nyse")
    assert assigned.loc[assigned.id == 2, "x_portfolio"].eq(1).all()
    assert assigned.loc[assigned.id == 8, "x_portfolio"].eq(2).all()
    assert set(assigned["y_portfolio"].dropna()) <= {1, 2, 3, 4}


def test_dependent_sort_conditions_later_breakpoints():
    assigned = assign_portfolios(panel(), ["x", "y"], [2, 2], reference="all", method="dependent")
    assert assigned[["x_portfolio", "y_portfolio"]].notna().all().all()


def test_lagging_and_ew_vw_returns():
    data = lag_characteristics(panel(), "x")
    assert data.groupby("id")["x_lag1"].nth(0).isna().all()
    assigned = assign_portfolios(panel(), "x", 2, reference="all")
    ew = portfolio_returns(assigned, "x_portfolio", weighting="ew")
    vw = portfolio_returns(assigned, "x_portfolio", weighting="vw")
    assert len(ew) == 4
    assert len(vw) == 2  # first month lacks beginning-of-month weights
    second_low = vw.loc[vw["x_portfolio"].eq(1), "ret"].iloc[0]
    assert np.isclose(second_low, np.average([.01, .02, .03, .04], weights=[1, 2, 3, 4]))
