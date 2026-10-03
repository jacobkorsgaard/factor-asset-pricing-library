import numpy as np
import pandas as pd

from factor_asset_pricing.sorts import (
    assign_annual_portfolios, assign_portfolios, lag_characteristics,
    portfolio_returns, quantile_breakpoints,
)


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


def test_explicit_30_70_breakpoints_and_lower_bucket_equality():
    values = pd.Series(np.arange(1, 11, dtype=float))
    assert np.array_equal(quantile_breakpoints(values, probabilities=[.3, .7]), [3., 7.])
    data = pd.DataFrame({"date": 1, "exchange": 1, "signal": values})
    assigned = assign_portfolios(
        data, "signal", breakpoint_probabilities={"signal": [.3, .7]}
    )
    assert assigned.loc[assigned.signal.eq(3), "signal_portfolio"].iloc[0] == 1
    assert assigned.loc[assigned.signal.eq(7), "signal_portfolio"].iloc[0] == 2
    assert assigned.loc[assigned.signal.eq(8), "signal_portfolio"].iloc[0] == 3


def test_explicit_conditioning_can_condition_two_signals_on_size_only():
    data = pd.DataFrame(
        {
            "date": 1,
            "exchange": 1,
            "size": np.arange(1, 9),
            "first": [1, 2, 3, 4, 1, 2, 3, 4],
            "second": [1, 50, 50, 100, 1, 50, 50, 100],
        }
    )
    assigned = assign_portfolios(
        data,
        ["size", "first", "second"],
        [2, 2, 2],
        reference="all",
        conditional_on={"first": ["size"], "second": ["size"]},
    )
    middle = assigned.loc[assigned.second.eq(50)]
    assert middle["second_portfolio"].eq(1).all()
    assert middle.groupby("size_portfolio")["first_portfolio"].nunique().eq(2).all()


def test_annual_formation_is_carried_from_july_through_following_june():
    dates = pd.date_range("2020-06-30", "2021-07-31", freq="ME")
    data = pd.DataFrame(
        [
            {"date": date, "id": security, "exchange": 1, "signal": float(security),
             "eligible": security != 4}
            for date in dates for security in range(1, 5)
        ]
    )
    result = assign_annual_portfolios(
        data, "signal", 2, reference="nyse", eligible="eligible"
    )
    assigned = result["panel"]
    holding = assigned.loc[assigned.date.between("2020-07-01", "2021-06-30")]
    assert holding.loc[holding.id.eq(1), "signal_portfolio"].eq(1).all()
    assert holding.loc[holding.id.eq(3), "signal_portfolio"].eq(2).all()
    assert holding.loc[holding.id.eq(4), "signal_portfolio"].isna().all()
    assert assigned.loc[assigned.date.eq(pd.Timestamp("2020-06-30")), "signal_portfolio"].isna().all()
    assert not result["breakpoints"].empty


def test_annual_assignment_can_prepare_all_ff5_sort_labels_together():
    data = pd.DataFrame(
        {
            "date": pd.Timestamp("2020-06-30"),
            "id": range(1, 11),
            "exchange": 1,
            "size": np.arange(1, 11, dtype=float),
            "bm": np.arange(1, 11, dtype=float),
            "op": np.arange(1, 11, dtype=float),
            "inv": np.arange(1, 11, dtype=float),
        }
    )
    result = assign_annual_portfolios(
        data,
        ["size", "bm", "op", "inv"],
        [2, 3, 3, 3],
        reference="nyse",
        breakpoint_probabilities={"bm": [.3, .7], "op": [.3, .7], "inv": [.3, .7]},
    )
    assert result["formation"][[
        "size_portfolio", "bm_portfolio", "op_portfolio", "inv_portfolio"
    ]].notna().all().all()
