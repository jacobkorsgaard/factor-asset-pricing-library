import numpy as np
import pandas as pd

from factor_asset_pricing.volatility_management import realized_variance, volatility_managed_return


def test_realized_variance_is_demeaned_sum_of_squares():
    x = pd.Series([.01, .03, -.02])
    assert np.isclose(realized_variance(x), ((x-x.mean())**2).sum())


def test_management_is_lagged_and_volatility_normalized():
    r = pd.Series([.02, -.01, .03, -.02, .04], index=range(5))
    rv = pd.Series([.001, .002, .003, .004, .005], index=range(5))
    result = volatility_managed_return(r, rv, normalize=True)
    assert result.lagged_measure.iloc[1] == rv.iloc[0]
    valid = result.managed_return.notna()
    assert np.isclose(result.loc[valid, "managed_return"].std(), r.loc[valid].std())
    ivol = volatility_managed_return(r, rv, scaling="inverse_volatility", normalize=False)
    assert np.isclose(ivol.weight.iloc[1], 1 / np.sqrt(rv.iloc[0]))



def test_unnormalized_management_uses_raw_inverse_variance_without_future_scaling():
    r = pd.Series([.02, -.01, .03, -.02])
    rv = pd.Series([.001, .002, .003, .004])
    result = volatility_managed_return(r, rv, normalize=False)
    np.testing.assert_allclose(result.weight.iloc[1:], 1 / rv.iloc[:-1].to_numpy())
    np.testing.assert_allclose(result.managed_return.iloc[1:], r.iloc[1:] / rv.shift(1).iloc[1:])
    changed_r, changed_rv = r.copy(), rv.copy()
    changed_r.iloc[-1], changed_rv.iloc[-1] = .8, .9
    changed = volatility_managed_return(changed_r, changed_rv, normalize=False)
    np.testing.assert_allclose(result.weight, changed.weight, equal_nan=True)
    np.testing.assert_allclose(result.managed_return.iloc[:-1], changed.managed_return.iloc[:-1], equal_nan=True)


def _calibration_inputs():
    rng = np.random.default_rng(42)
    dates = pd.date_range('1960-01-01', periods=160, freq='MS')
    returns = pd.DataFrame(rng.normal(.005, .03, size=(160, 2)), index=dates, columns=['early', 'late'])
    returns.loc[dates[:12], 'late'] = np.nan
    variance = pd.DataFrame(rng.uniform(.0005, .004, size=(160, 2)), index=dates, columns=returns.columns)
    return returns, variance


def test_calibration_uses_initial_ten_shared_years_and_only_returns_later_months():
    from factor_asset_pricing.volatility_management import calibrate_volatility_management

    returns, variance = _calibration_inputs()
    result = calibrate_volatility_management(returns, variance)
    calibration, evaluation = result['calibration_index'], result['evaluation_index']
    assert len(calibration) == 120
    assert calibration[0] == pd.Timestamp('1961-01-01')
    assert calibration[-1] == pd.Timestamp('1970-12-01')
    assert evaluation[0] == pd.Timestamp('1971-01-01')
    assert result['original'].index.equals(evaluation)
    raw = returns / variance.shift(1)
    expected_scale = returns.loc[calibration].std() / raw.loc[calibration].std()
    pd.testing.assert_series_equal(result['scale'], expected_scale)
    np.testing.assert_allclose(raw.loc[calibration].mul(result['scale']).std(), returns.loc[calibration].std())
    np.testing.assert_allclose(result['managed'], raw.loc[evaluation].mul(expected_scale))
    np.testing.assert_allclose(result['weights'].iloc[0], expected_scale / variance.loc[calibration[-1]])
    np.testing.assert_allclose(result['managed'], result['weights'] * result['original'])
    # Risk is matched only in training, not retrospectively in evaluation.
    assert not np.allclose(result['managed'].std(), result['original'].std())


def test_future_data_cannot_change_calibration_or_earlier_evaluation_positions():
    from factor_asset_pricing.volatility_management import calibrate_volatility_management

    returns, variance = _calibration_inputs()
    original = calibrate_volatility_management(returns, variance)
    future = original['evaluation_index'][5:]
    returns.loc[future] *= 10
    variance.loc[future] *= 20
    changed = calibrate_volatility_management(returns, variance)
    pd.testing.assert_series_equal(original['scale'], changed['scale'])
    earlier = original['evaluation_index'][:5]
    pd.testing.assert_frame_equal(original['weights'].loc[earlier], changed['weights'].loc[earlier])
    pd.testing.assert_frame_equal(original['managed'].loc[earlier], changed['managed'].loc[earlier])


def test_calibration_rejects_internal_missing_months_and_insufficient_history():
    import pytest
    from factor_asset_pricing.volatility_management import calibrate_volatility_management

    returns, variance = _calibration_inputs()
    with pytest.raises(ValueError, match='consecutive'):
        calibrate_volatility_management(returns.drop(returns.index[50]), variance)
    broken = returns.copy()
    broken.loc[broken.index[50], 'late'] = np.nan
    with pytest.raises(ValueError, match='missing observations'):
        calibrate_volatility_management(broken, variance)
    with pytest.raises(ValueError, match='out-of-sample'):
        calibrate_volatility_management(returns.iloc[:132], variance)
