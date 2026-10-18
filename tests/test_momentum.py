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
    momentum_signal_panel,
    prepare_momentum_data,
    size_balanced_stock_momentum,
    time_series_stock_momentum,
    momentum_portfolio_returns,
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


def test_panel_signals_match_security_signals_with_gaps_and_losses():
    def panel_signal(frame, lookback, skip):
        return momentum_signal_panel(frame, lookback=lookback, skip=skip,
                                     id_col='permno', date_col='mdate', return_col='retadj')
    dates = pd.date_range('2000-01-01', periods=18, freq='MS')
    a = pd.DataFrame({'permno': 1, 'mdate': dates, 'retadj': [.01, -.02, -1, np.nan] + [.03] * 14})
    b = pd.DataFrame({'permno': 2, 'mdate': dates.delete(5), 'retadj': .02})
    frame = pd.concat([a, b], ignore_index=True)
    for lookback in [1, 3, 6, 12]:
        for skip in [1, 2]:
            actual = panel_signal(frame, lookback, skip)
            expected = pd.concat([
                momentum_signal(g.retadj, lookback=lookback, skip=skip, dates=g.mdate)
                for _, g in frame.groupby('permno')]).reindex(frame.index)
            pd.testing.assert_series_equal(actual, expected, check_names=False, atol=1e-12, rtol=1e-12)
    # Changing month t's payoff must not change month t's position signal.
    changed = frame.copy()
    changed.loc[12, 'retadj'] = -.8
    assert panel_signal(frame, 6, 1).loc[12] == panel_signal(changed, 6, 1).loc[12]


def test_panel_signals_preserve_unsorted_rows_and_repeated_index_labels():
    frame = pd.DataFrame({'id': [2, 1, 2, 1],
        'date': pd.to_datetime(['2020-02-01', '2020-01-01', '2020-01-01', '2020-02-01']),
        'ret': [.3, .1, -.2, .4]}, index=[7, 7, 3, 3])
    actual = momentum_signal_panel(frame, lookback=1)
    assert actual.index.equals(frame.index)
    np.testing.assert_allclose(actual, [-.2, np.nan, np.nan, .1], equal_nan=True)
    with pytest.raises(ValueError, match='unique'):
        momentum_signal_panel(pd.concat([frame, frame.iloc[[0]]]), lookback=1)


def test_preparation_lags_inputs_by_calendar_month_and_aligns_rf():
    dates = pd.to_datetime(['2020-01-31', '2020-02-29', '2020-04-30'])
    data = pd.DataFrame({'id': 1, 'date': dates, 'ret': [.1, .2, .3],
                         'market_equity': [10., 20., 30.], 'exchange': [1, 2, 3]})
    rf = pd.Series([.001, .002, .003], index=dates.to_period('M').to_timestamp()).iloc[::-1]
    prepared = prepare_momentum_data(data, rf)
    np.testing.assert_allclose(prepared.lag_me, [np.nan, 10., np.nan], equal_nan=True)
    np.testing.assert_allclose(prepared.lag_exchange, [np.nan, 1, np.nan], equal_nan=True)
    np.testing.assert_allclose(prepared.excess, [.099, .198, .297])
    with pytest.raises(ValueError, match='cover every'):
        prepare_momentum_data(data, rf.iloc[:1])


def _prepared_momentum_cross_section():
    return pd.DataFrame({'id': range(8), 'date': pd.Timestamp('2020-02-01'),
        'momentum': [-.4, -.3, .3, .4] * 2, 'lag_me': [1.] * 4 + [10.] * 4,
        'lag_exchange': 1, 'ret': [.01, .03, .04, .08, .02, .04, .05, .10],
        'rf': .002}).assign(excess=lambda x: x.ret - x.rf)


def test_size_balanced_stock_momentum_uses_equal_size_legs_and_signed_short():
    panel = _prepared_momentum_cross_section()
    result = size_balanced_stock_momentum(panel).iloc[0]
    assert result['Long only'] == pytest.approx(.09 - .002)
    assert result['Short only'] == pytest.approx(-(.025 - .002))
    assert result['Combined'] == pytest.approx(.065)
    # A change in unavailable future returns cannot change formation cutoffs.
    panel.loc[0, ['ret', 'excess']] = np.nan
    result = size_balanced_stock_momentum(panel).iloc[0]
    assert result['Long only'] == pytest.approx(.088)
    assert result['Short only'] == pytest.approx(-(.03 - .002))


def test_time_series_stock_momentum_financing_and_zero_signal_cash():
    panel = _prepared_momentum_cross_section()
    panel.loc[2, 'momentum'] = 0
    panel.loc[7, ['ret', 'excess']] = np.nan
    payoffs, exposure = time_series_stock_momentum(panel)
    weights = panel.lag_me.where(panel.ret.notna(), 0)
    weights = weights / weights.sum() * np.sign(panel.momentum)
    expected = (weights * panel.excess).sum()
    assert payoffs.iloc[0]['Combined'] == pytest.approx(expected)
    assert exposure.iloc[0]['net'] == pytest.approx(weights.sum())
    assert exposure.iloc[0]['gross'] == pytest.approx(weights.abs().sum())
    assert exposure.iloc[0]['gross'] < 1
    assert payoffs.iloc[0]['Combined'] == pytest.approx(
        (weights * panel.ret).sum() - weights.sum() * .002)
    assert payoffs.iloc[0]['Combined'] == pytest.approx(payoffs.iloc[0]['Long only'] + payoffs.iloc[0]['Short only'])


def test_stock_portfolios_use_formation_cutoffs_before_missing_return_exclusion():
    panel = _prepared_momentum_cross_section()
    panel.loc[0, ['ret', 'excess']] = np.nan
    returns = momentum_portfolio_returns(panel, n_portfolios=2).iloc[0]
    assert returns.P1 == pytest.approx((.03 + 10 * .02 + 10 * .04) / 21)
    assert returns.P2 == pytest.approx((.04 + .08 + 10 * .05 + 10 * .10) / 22)


def test_missing_reference_or_holding_returns_do_not_create_zero_payoffs():
    panel = _prepared_momentum_cross_section()
    panel['lag_exchange'] = 2
    assert size_balanced_stock_momentum(panel).isna().all().all()
    assert momentum_portfolio_returns(panel).isna().all().all()
    panel[['ret', 'excess']] = np.nan
    payoffs, exposure = time_series_stock_momentum(panel)
    assert payoffs.isna().all().all() and exposure.isna().all().all()
