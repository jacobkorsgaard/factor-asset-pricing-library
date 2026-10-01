import numpy as np
import pandas as pd

from factor_asset_pricing.volatility_management import realized_variance, volatility_managed_return


def test_realized_variance_is_demeaned_sum_of_squares():
    x = pd.Series([.01, .03, -.02])
    assert np.isclose(realized_variance(x), ((x-x.mean())**2).sum())


def test_management_is_lagged_and_volatility_normalized():
    r = pd.Series([.02, -.01, .03, -.02, .04], index=range(5))
    rv = pd.Series([.001, .002, .003, .004, .005], index=range(5))
    result = volatility_managed_return(r, rv)
    assert result.lagged_measure.iloc[1] == rv.iloc[0]
    valid = result.managed_return.notna()
    assert np.isclose(result.loc[valid, "managed_return"].std(), r.loc[valid].std())
    ivol = volatility_managed_return(r, rv, scaling="inverse_volatility", normalize=False)
    assert np.isclose(ivol.weight.iloc[1], 1 / np.sqrt(rv.iloc[0]))

