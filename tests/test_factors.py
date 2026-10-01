import numpy as np
import pandas as pd

from factor_asset_pricing.factors import fama_french_2x3_factor, market_excess_return


def test_ff_2x3_cell_averaging_and_legs():
    cells = pd.DataFrame([
        {"date": 1, "size": s, "char": q, "ret": 10*s + q}
        for s in [1, 2] for q in [1, 2, 3]
    ])
    result = fama_french_2x3_factor(cells, size_col="size", characteristic_col="char")
    assert result.HML.iloc[0] == 2
    assert result.SMB.iloc[0] == -10
    assert result.HML_long.iloc[0] == 18


def test_market_excess_return_uses_lagged_value_weights():
    dates = pd.date_range("2020-01-31", periods=2, freq="ME")
    data = pd.DataFrame({"date": np.repeat(dates, 2), "id": [1, 2]*2,
                         "ret": [.01, .03, .02, .04], "market_equity": [1, 3, 2, 4], "rf": .005})
    result = market_excess_return(data)
    assert len(result) == 1
    assert np.isclose(result.MKT.iloc[0], np.average([.02, .04], weights=[1, 3]) - .005)

