import numpy as np
import pandas as pd

from factor_asset_pricing.momentum import factor_momentum, factor_momentum_positions, momentum_signal


def test_stock_signal_lookback_and_skip():
    returns = pd.Series([.1, .2, .3, .4])
    signal = momentum_signal(returns, lookback=2, skip=1)
    assert np.isnan(signal.iloc[1])
    assert np.isclose(signal.iloc[2], 1.1 * 1.2 - 1)


def test_factor_momentum_uses_only_prior_window():
    factors = pd.DataFrame({"up": [.01]*12 + [-.2], "down": [-.01]*12 + [.2]})
    positions = factor_momentum_positions(factors, lookback=12, skip=1)
    assert positions.iloc[12].to_dict() == {"up": .5, "down": -.5}
    assert np.isclose(factor_momentum(factors).iloc[12], -.2)


def test_overlapping_factor_momentum_holds_average_vintages():
    factors = pd.DataFrame({"f": [.1, -.3, .1, .1]})
    positions = factor_momentum_positions(factors, lookback=1, skip=1, holding_period=2)
    assert positions.iloc[2, 0] == 0  # +1 and -1 active vintages

