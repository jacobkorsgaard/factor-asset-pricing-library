import numpy as np
import pandas as pd

from factor_asset_pricing.characteristics import (
    adjusted_return, book_equity, investment, market_equity, operating_profitability,
)


def test_adjusted_return_includes_delisting_payoff():
    ret = pd.Series([.10, .10, np.nan, np.nan])
    dlret = pd.Series([-.50, np.nan, -.25, np.nan])
    result = adjusted_return(ret, dlret)
    assert np.isclose(result.iloc[0], (1.1 * .5) - 1)
    assert result.iloc[1] == .10
    assert result.iloc[2] == -.25
    assert np.isnan(result.iloc[3])


def test_market_and_book_equity_conventions():
    me = market_equity(pd.Series([-2., 3.]), pd.Series([10., 0.]))
    assert me.iloc[0] == 20
    assert np.isnan(me.iloc[1])
    be = book_equity(
        pd.Series([100., 10.]), pd.Series([5., np.nan]), pd.Series([2., np.nan]),
        pd.Series([3., 20.]), pd.Series([4., 1.]),
    )
    assert be.iloc[0] == 103
    assert np.isnan(be.iloc[1])


def test_profitability_and_investment_definitions():
    op = operating_profitability(
        pd.Series([100.]), pd.Series([40.]), pd.Series([10.]), pd.Series([5.]), pd.Series([50.])
    )
    assert np.isclose(op.iloc[0], .9)
    assets = pd.Series([100., 120., 50., 75.])
    firms = pd.Series([1, 1, 2, 2])
    growth = investment(assets, group=firms)
    assert np.isclose(growth.iloc[1], .2)
    assert np.isclose(growth.iloc[3], .5)

