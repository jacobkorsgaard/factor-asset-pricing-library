"""Small synthetic original-format fixtures; no network or third-party data."""
import io
from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from factor_asset_pricing.french_data import load_french, sample_coverage, source_url


def write_ff3(tmp_path, rows="196307,1,2,-99.99,0.2\n196308,-1,-999,3,0.1"):
    payload = ("Original metadata\n\n,Mkt-RF,SMB,HML,RF\n" + rows +
               "\n\n Annual Returns\n, Mkt-RF,SMB,HML,RF\n1963,99,99,99,99\n").encode()
    path = tmp_path / "F-F_Research_Data_Factors.csv"
    path.write_bytes(payload)
    return path, payload


def test_monthly_units_sentinels_and_annual_exclusion(tmp_path):
    path, payload = write_ff3(tmp_path)
    frame = load_french("ff3", tmp_path, download=False)
    assert list(frame) == ["MKT", "SMB", "HML", "RF"]
    assert frame.index.equals(pd.date_range("1963-07-01", periods=2, freq="MS", name="date"))
    assert frame.iloc[0].MKT == .01 and frame.iloc[0].RF == .002
    assert np.isnan(frame.iloc[0].HML) and np.isnan(frame.iloc[1].SMB)
    assert path.read_bytes() == payload
    assert len(frame.attrs['sha256']) == 64
    assert sample_coverage(frame).loc['HML', 'missing'] == 1


@pytest.mark.parametrize("rows", ["196307,1,2,3,4\n196307,1,2,3,4",
                                   "196308,1,2,3,4\n196307,1,2,3,4",
                                   "196307,1,2,3,4\n196309,1,2,3,4",
                                   "196313,1,2,3,4", "196307,1,2,3"])
def test_invalid_dates_gaps_and_width_raise(tmp_path, rows):
    write_ff3(tmp_path, rows)
    with pytest.raises(ValueError):
        load_french("ff3", tmp_path, download=False)


def test_daily_trading_dates_not_calendar_filled(tmp_path):
    (tmp_path / 'F-F_Momentum_Factor_daily.csv').write_text(
        'metadata\n,Mom\n20240105,1.5\n20240108,-2\n')
    frame = load_french('momentum', tmp_path, frequency='daily', download=False)
    assert list(frame) == ['MOM']
    assert frame.index.tolist() == [pd.Timestamp('2024-01-05'), pd.Timestamp('2024-01-08')]
    assert frame.MOM.tolist() == [.015, -.02]


def test_selects_value_weighted_returns_and_momentum_columns(tmp_path):
    header = ',Lo PRIOR,' + ','.join(f'PRIOR {i}' for i in range(2, 10)) + ',Hi PRIOR'
    (tmp_path / '10_Portfolios_Prior_12_2.csv').write_text(
        'metadata\n Value Weight Returns -- Monthly\n' + header + '\n196307,' +
        ','.join(str(i) for i in range(1, 11)) + '\n\n Equal Weight Returns -- Monthly\n' +
        header + '\n196307,' + ','.join(['99']*10))
    frame = load_french('momentum_deciles', tmp_path, download=False)
    assert list(frame) == [f'P{i}' for i in range(1, 11)]
    assert frame.iloc[0].P10 == .1 and frame.iloc[0].P1 == .01


def test_rank_order_checked_before_renaming(tmp_path):
    names = [f'ME{s} BM{c}' for s in range(1, 6) for c in range(1, 6)]
    path = tmp_path / '25_Portfolios_5x5.csv'
    def write(names):
        path.write_text('metadata\n Average Value Weighted Returns -- Monthly\n,' +
                        ','.join(names) + '\n196307,' + ','.join(str(i) for i in range(25)))
    write(names)
    frame = load_french('size_bm', tmp_path, download=False)
    assert frame.iloc[0]['S2C1'] == .05 and frame.iloc[0]['S5C5'] == .24
    names[0], names[1] = names[1], names[0]
    write(names)
    with pytest.raises(ValueError, match='order'):
        load_french('size_bm', tmp_path, download=False)


def test_zip_download_preserves_bytes_and_offline_reuse(tmp_path, monkeypatch):
    _, csv_bytes = write_ff3(tmp_path)
    (tmp_path / 'F-F_Research_Data_Factors.csv').unlink()
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as archive:
        archive.writestr('F-F_Research_Data_Factors.csv', csv_bytes)
    payload = buffer.getvalue()
    calls = []
    def download(url, timeout):
        calls.append(url)
        return io.BytesIO(payload)
    monkeypatch.setattr('factor_asset_pricing.french_data.urlopen', download)
    first = load_french('ff3', tmp_path)
    assert calls == [source_url('ff3')]
    assert (tmp_path / 'F-F_Research_Data_Factors_CSV.zip').read_bytes() == payload
    pd.testing.assert_frame_equal(first, load_french('ff3', tmp_path, download=False))
    assert len(calls) == 1
    assert not list(tmp_path.glob('*.download'))


def test_malformed_local_source_is_not_replaced(tmp_path, monkeypatch):
    path, payload = write_ff3(tmp_path)
    path.write_bytes(payload.replace(b'SMB', b'WRONG'))
    monkeypatch.setattr('factor_asset_pricing.french_data.urlopen', lambda *a, **k: pytest.fail('network used'))
    with pytest.raises(ValueError, match='columns'):
        load_french('ff3', tmp_path)


def test_failed_download_not_saved(tmp_path, monkeypatch):
    monkeypatch.setattr('factor_asset_pricing.french_data.urlopen', lambda *a, **k: io.BytesIO(b'<html>error</html>'))
    with pytest.raises(ValueError):
        load_french('ff3', tmp_path)
    assert not list(tmp_path.iterdir())


def test_missing_offline_and_frequency_validation(tmp_path):
    with pytest.raises(FileNotFoundError, match='https://mba.tuck'):
        load_french('ff5', tmp_path, download=False)
    with pytest.raises(ValueError):
        source_url('ff5', 'annual')
    with pytest.raises(ValueError):
        source_url('size', 'daily')
    with pytest.raises(ValueError):
        source_url('unknown')


def test_three_way_corner_labels_and_size_major_order(tmp_path):
    names = [f'ME{s} BM{a} OP{b}' for s in [1, 2] for a in range(1, 5) for b in range(1, 5)]
    names[0] = 'SMALL LoBM LoOP'
    names[-1] = 'BIG HiBM HiOP'
    (tmp_path / '32_Portfolios_ME_BEME_OP_2x4x4.csv').write_text(
        'metadata\n Average Value Weighted Returns -- Monthly\n,' + ','.join(names) +
        '\n196307,' + ','.join(str(i) for i in range(32)))
    frame = load_french('size_bm_op', tmp_path, download=False)
    assert frame.iloc[0]['S-1-1'] == 0
    assert frame.iloc[0]['S-4-4'] == .15
    assert frame.iloc[0]['B-1-1'] == .16
    assert frame.iloc[0]['B-4-4'] == .31


def test_size_quintiles_exclude_negative_size_and_deciles(tmp_path):
    (tmp_path / 'Portfolios_Formed_on_ME.csv').write_text(
        'metadata\n Average Value Weight Returns -- Monthly\n'
        ',<= 0,Lo 20,Qnt 2,Qnt 3,Qnt 4,Hi 20,Lo 10\n196307,-99.99,1,2,3,4,5,99\n')
    frame = load_french('size', tmp_path, download=False)
    assert list(frame) == ['Small', '2', '3', '4', 'Big']
    assert frame.iloc[0].tolist() == [.01, .02, .03, .04, .05]
