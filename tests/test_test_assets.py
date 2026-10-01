import numpy as np
import pandas as pd

from factor_asset_pricing.test_assets import portfolio_average_characteristics, to_excess_returns


def test_portfolio_average_characteristics_and_excess_returns():
    data = pd.DataFrame({"date": [1, 1], "p": [1, 1], "x": [1., 3.], "market_equity": [1., 3.]})
    assert portfolio_average_characteristics(data, "p", "x").x.iloc[0] == 2
    assert portfolio_average_characteristics(data, "p", "x", weighting="vw").x.iloc[0] == 2.5
    returns = pd.DataFrame({"date": [1], "ret": [.03]})
    rf = pd.DataFrame({"date": [1], "rf": [.01]})
    assert np.isclose(to_excess_returns(returns, rf).ret.iloc[0], .02)

