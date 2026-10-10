import numpy as np
import pandas as pd
import pytest

from factor_asset_pricing.momentum import (
    conditional_future_returns,
    cross_sectional_momentum,
    cross_sectional_momentum_positions,
    factor_momentum,
    factor_momentum_positions,
    lagged_correlation_matrix,
    momentum_signal,
    stock_momentum,
)


def test_signal_rejects_calendar_gap_between_window_and_holding_month():
    dates = pd.to_datetime(['2020-01-31', '2020-02-29', '2020-04-30'])
    signal = momentum_signal(pd.Series([.1, .2, .3]), lookback=2, skip=1, dates=dates)
    assert signal.isna().all()


def test_intentional_skip_excludes_returns_without_creating_calendar_gap():
    dates = pd.date_range('2020-01-31', periods=4, freq='ME')
    signal = momentum_signal(pd.Series([.1, .2, -.9, .8]), lookback=2, skip=2, dates=dates)
    assert signal.iloc[3] == pytest.approx(1.1 * 1.2 - 1)


def test_signal_rejects_duplicate_and_unordered_months():
    for dates in [['2020-01-01', '2020-01-31', '2020-03-31'],
                  ['2020-02-29', '2020-01-31', '2020-03-31']]:
        with pytest.raises(ValueError, match='unique.*increasing'):
            momentum_signal(pd.Series([.1, .2, .3]), lookback=2, dates=pd.to_datetime(dates))


def test_stock_signal_lookback_and_skip():
    returns = pd.Series([.1, .2, .3, .4])
    signal = momentum_signal(returns, lookback=2, skip=1)
    assert np.isnan(signal.iloc[1])
    assert np.isclose(signal.iloc[2], 1.1 * 1.2 - 1)


def test_signal_with_dates_rejects_nonconsecutive_months():
    returns = pd.Series([.1, .2, .3])
    dates = pd.Series(pd.to_datetime(["2020-01-31", "2020-03-31", "2020-04-30"]))
    signal = momentum_signal(returns, lookback=2, skip=1, dates=dates)
    assert signal.isna().all()


def test_signal_allows_total_loss_but_rejects_returns_below_minus_one():
    signal = momentum_signal(pd.Series([-1.0, .2]), lookback=1, skip=1)
    assert signal.iloc[1] == -1
    with np.testing.assert_raises(ValueError):
        momentum_signal(pd.Series([-1.01, .2]), lookback=1, skip=1)


def test_conditional_returns_do_not_fill_missing_observations():
    returns = pd.DataFrame({"asset": [.1, .2, np.nan, -.2, .3, .4]})
    result = conditional_future_returns(returns, lookback=1, skip=1)
    assert result.loc["asset", "n_positive"] == 2
    assert result.loc["asset", "n_negative"] == 1


def test_factor_momentum_uses_only_prior_window():
    factors = pd.DataFrame({"up": [.01]*12 + [-.2], "down": [-.01]*12 + [.2]})
    positions = factor_momentum_positions(factors, lookback=12, skip=1)
    assert positions.iloc[12].to_dict() == {"up": .5, "down": -.5}
    assert np.isclose(factor_momentum(factors).iloc[12], -.2)


def test_overlapping_factor_momentum_holds_average_vintages():
    factors = pd.DataFrame({"f": [.1, -.3, .1, .1]})
    positions = factor_momentum_positions(factors, lookback=1, skip=1, holding_period=2)
    assert positions.iloc[2, 0] == 0  # +1 and -1 active vintages


def test_factor_momentum_normalizes_over_currently_available_factors():
    factors = pd.DataFrame(
        {"a": [.1, .2], "b": [-.1, -.2], "missing": [.1, np.nan]}
    )
    positions = factor_momentum_positions(factors, lookback=1, skip=1)
    assert np.isclose(positions.iloc[1].abs().sum(), 1)
    assert np.isnan(positions.loc[1, "missing"])


def test_cross_sectional_positions_are_dollar_neutral_and_unit_gross():
    returns = pd.DataFrame(
        {
            "a": [-.20, .01],
            "b": [-.10, .02],
            "c": [.10, .03],
            "d": [.20, .04],
        }
    )
    positions = cross_sectional_momentum_positions(returns, lookback=1, skip=1)
    assert np.isclose(positions.iloc[1].sum(), 0)
    assert np.isclose(positions.iloc[1].abs().sum(), 1)
    strategy = cross_sectional_momentum(returns, lookback=1, skip=1)
    assert strategy.iloc[1] > 0


def test_stock_momentum_assigns_winners_long_and_losers_short():
    dates = pd.date_range("2020-01-31", periods=3, freq="ME")
    first_returns = {1: -.20, 2: -.10, 3: .10, 4: .20}
    later_returns = {1: -.02, 2: -.01, 3: .03, 4: .04}
    rows = []
    for date_number, date in enumerate(dates):
        for security in range(1, 5):
            rows.append(
                {
                    "date": date,
                    "id": security,
                    "exchange": 1,
                    "ret": first_returns[security] if date_number == 0 else later_returns[security],
                    "market_equity": 1.0,
                }
            )
    factor, portfolios = stock_momentum(
        pd.DataFrame(rows), lookback=1, skip=1, n_portfolios=2,
        reference="all", weighting="ew",
    )
    month_two = portfolios.loc[portfolios.date.eq(dates[1])].set_index("momentum_portfolio")
    assert month_two.loc[2, "ret"] > month_two.loc[1, "ret"]
    assert factor.loc[factor.date.eq(dates[1]), "MOM"].iloc[0] > 0


def test_stock_momentum_carries_original_labels_across_holding_months():
    dates = pd.date_range("2020-01-31", periods=4, freq="ME")
    returns = {
        1: [-.20, .30, .01, .01],
        2: [-.10, .20, .01, .01],
        3: [.10, -.20, .05, .05],
        4: [.20, -.30, .05, .05],
    }
    rows = [
        {
            "date": date,
            "id": security,
            "exchange": 1,
            "ret": returns[security][month],
            "market_equity": 1.0,
        }
        for month, date in enumerate(dates)
        for security in returns
    ]
    factor, _ = stock_momentum(
        pd.DataFrame(rows), lookback=1, skip=1, holding_period=2,
        n_portfolios=2, reference="all", weighting="ew",
    )
    # In month three the newest vintage reverses labels, while the older
    # vintage keeps its month-two labels. Their opposing spreads average to 0.
    month_three = factor.loc[factor.date.eq(dates[2]), "MOM"].iloc[0]
    assert np.isclose(month_three, 0)


def test_lagged_correlation_matrix_has_current_rows_and_lagged_columns():
    returns = pd.DataFrame({"a": [1., 2., 3., 4.], "b": [2., 4., 6., 8.]})
    matrix = lagged_correlation_matrix(returns)
    assert list(matrix.index) == ["a", "b"]
    assert list(matrix.columns) == ["a", "b"]
    assert np.isclose(matrix.loc["a", "b"], 1)
