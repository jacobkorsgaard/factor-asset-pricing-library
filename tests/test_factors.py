import numpy as np
import pandas as pd

from factor_asset_pricing.factors import (
    fama_french_2x3_factor, fama_french_five_factors, market_excess_return,
)


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


def test_ff5_composes_three_smb_components_and_factor_directions():
    rows = []
    for size in [1, 2]:
        for group in [1, 2, 3]:
            rows.append(
                {
                    "date": pd.Timestamp("2020-01-31"), "id": 10 * size + group,
                    "size_portfolio": size, "bm_portfolio": group,
                    "op_portfolio": group, "inv_portfolio": group,
                    "ret": .03 * (size - 1) + .01 * group,
                    "market_equity": 1., "rf": .001,
                }
            )
    result = fama_french_five_factors(pd.DataFrame(rows), lag_weights=False)
    factors = result["factors"].iloc[0]
    assert np.isclose(factors.HML, .02)
    assert np.isclose(factors.RMW, .02)
    assert np.isclose(factors.CMA, -.02)
    assert np.isclose(factors.SMB, -.03)
    assert np.isclose(result["components"].SMB_long.iloc[0], .02)
    assert np.isclose(result["components"].SMB_short.iloc[0], .05)
    assert set(result["cells"]) == {"value", "profitability", "investment"}

    labelled = pd.DataFrame(rows).replace(
        {
            "size_portfolio": {1: "S", 2: "B"},
            "bm_portfolio": {1: "L", 2: "M", 3: "H"},
            "op_portfolio": {1: "W", 2: "M", 3: "R"},
            "inv_portfolio": {1: "C", 2: "M", 3: "A"},
        }
    )
    labelled_result = fama_french_five_factors(
        labelled,
        lag_weights=False,
        size_labels=("S", "B"),
        value_labels=("L", "M", "H"),
        profitability_labels=("W", "M", "R"),
        investment_labels=("C", "M", "A"),
    )
    assert np.isclose(labelled_result["factors"].CMA.iloc[0], -.02)
