"""Synthetic observations only: dates, links, availability and financial timing."""
import numpy as np
import pandas as pd
import pytest

from factor_asset_pricing.data_preparation import (
    clean_crsp, clean_compustat, clean_ccm, link_crsp_compustat,
    attach_annual_accounts, prepare_risk_free, previous_month_weights,
    validate_prepared_panel,
)
from factor_asset_pricing.wrds_data import (
    ACCOUNTING_COLUMNS, REQUIRED_COLUMNS, SOURCE_FILES,
    read_wrds_export, load_prepared_data, save_prepared_data,
)
from factor_asset_pricing.construction import characteristic_panel, annual_ff5_assignments


def crsp_rows(dates=('2020-06-30', '2020-07-31'), ids=(1,)):
    return pd.DataFrame([dict(permno=i, date=d, shrcd=10, exchcd=1, ret=.1,
                             dlret=np.nan, prc=-10., shrout=100.) for i in ids for d in dates])


def accounts(years=(2018, 2019), company='000001'):
    return pd.DataFrame([dict(gvkey=company, datadate=f'{y}-12-31', fyear=y,
        at=100*(1.2**j), seq=50., txditc=5., pstkrv=2., pstkl=3., pstk=4.,
        revt=100., cogs=40., xsga=10., xint=5.,
        indfmt='INDL', datafmt='STD', consol='C', curcd='USD', costat='I')
        for j, y in enumerate(years)])


def links(start='2010-01-01', end='2020-07-31', company='000001', prim='P', typ='LU'):
    return pd.DataFrame([dict(gvkey=company, lpermno=1, linkprim=prim,
                             linktype=typ, linkdt=start, linkenddt=end)])


def test_rtf_reader_removes_end_suffix_preserves_scientific_and_gvkey(tmp_path):
    p = tmp_path/'source.csv'
    original = r'{\rtf1\ansi' + '\n' + r'\f0\fs24 GVKEY,LINKENDDT,AT' + '\\' + '\n' + '000001,2020-07-31,1.2E+02\\\n}\n'
    p.write_text(original)
    d = read_wrds_export(p, ['gvkey', 'linkenddt', 'at'])
    assert d.gvkey.iloc[0] == '000001'
    assert d.linkenddt.iloc[0] == '2020-07-31'
    assert d['at'].iloc[0] == 120
    assert p.read_text() == original


def test_plain_csv_case_and_required_header(tmp_path):
    p = tmp_path/'source.csv';p.write_text('GVKEY,AT\n000001,120\n')
    assert read_wrds_export(p, ['gvkey', 'at']).gvkey.iloc[0] == '000001'
    with pytest.raises(ValueError, match='header'):
        read_wrds_export(p, ['missing'])


def test_crsp_units_flags_and_delisting_only():
    d = crsp_rows(dates=('2020-06-30', '2020-07-31', '2020-08-31'))
    d['ret'] = ['C', .1, -88]
    d['dlret'] = [-.25, -.5, np.nan]
    result = clean_crsp(d)
    assert result.mdate.iloc[0] == pd.Timestamp('2020-06-01')
    assert result.retadj.iloc[0] == -.25
    assert np.isclose(result.retadj.iloc[1], -.45)
    assert np.isnan(result.retadj.iloc[2])
    assert result.me.eq(1000).all()
    assert result.prc.eq(-10).all()  # quotation flag preserved


@pytest.mark.parametrize('kind', ['duplicate', 'return', 'identifier', 'numeric'])
def test_bad_crsp_is_not_silently_cleaned(kind):
    d = crsp_rows()
    if kind == 'duplicate': d = pd.concat([d, d.iloc[[0]]])
    if kind == 'return': d.loc[0, 'ret'] = -2.
    if kind == 'identifier':
        d['permno']=d.permno.astype(float);d.loc[0, 'permno'] = 1.5
    if kind == 'numeric':
        d['prc']=d.prc.astype(object);d.loc[0, 'prc'] = 'bad'
    with pytest.raises(ValueError): clean_crsp(d)


def test_historical_security_filters_do_not_delete_entire_security():
    d=crsp_rows();d.loc[0, 'shrcd']=12
    out=clean_crsp(d)
    assert len(out)==1 and out.mdate.iloc[0]==pd.Timestamp('2020-07-01')


def test_account_filters_keep_inactive_and_deduplicate_latest():
    d=accounts();bad=d.iloc[[0]].copy();bad['curcd']='CAD'
    result=clean_compustat(pd.concat([d, d.iloc[[0]], bad]))
    assert len(result)==2 and result.gvkey.eq('000001').all()
    assert result.available_from.iloc[-1]==pd.Timestamp('2020-07-01')
    assert result.formation_date.iloc[-1]==pd.Timestamp('2020-06-30')
    assert result.attrs['diagnostics']['excluded_or_duplicate_rows']==2


def test_conflicting_accounts_raise():
    d=accounts();other=d.iloc[[0]].copy();other['seq']=100
    with pytest.raises(ValueError, match='Conflicting'):
        clean_compustat(pd.concat([d, other]))


def test_ccm_endpoints_open_codes_and_midmonth_boundary():
    c=clean_crsp(crsp_rows())
    closed=clean_ccm(links(start='2020-06-15', end='2020-07-15'))
    out=link_crsp_compustat(c, closed)
    assert len(out)==1 and out.mdate.iloc[0]==pd.Timestamp('2020-07-01')
    opened=clean_ccm(links(start='.B', end='.E'))
    assert len(link_crsp_compustat(c, opened))==2
    with pytest.raises(ValueError, match='start follows'):
        clean_ccm(links(start='2021-01-01', end='2020-01-01'))
    with pytest.raises(ValueError): clean_ccm(links(end='not-a-date'))


def test_ccm_priorities_and_ambiguous_ties():
    c=clean_crsp(crsp_rows())
    l=pd.concat([links(company='000002', prim='C'), links(company='000001', prim='P')])
    assert link_crsp_compustat(c, clean_ccm(l)).gvkey.eq('000001').all()
    l=pd.concat([links(company='000002', typ='LC'), links(company='000001', typ='LU')])
    assert link_crsp_compustat(c, clean_ccm(l)).gvkey.eq('000001').all()
    with pytest.raises(ValueError, match='Ambiguous'):
        link_crsp_compustat(c, clean_ccm(pd.concat([links(), links(company='000002')])))


def test_annual_carriers_start_in_july_and_expire():
    c=clean_crsp(crsp_rows(dates=('2020-06-30', '2020-07-31', '2021-06-30', '2021-07-31')))
    linked=link_crsp_compustat(c, clean_ccm(links(end='.E')))
    out=attach_annual_accounts(linked, clean_compustat(accounts(years=(2019,))))
    assert out.fyear.tolist()[1:3]==[2019,2019]
    assert pd.isna(out.fyear.iloc[0]) and pd.isna(out.fyear.iloc[3])


def test_treasury_conversion_and_undated_placeholder():
    d=pd.DataFrame({'mcaldt':['2020-01-31','2020-01-31',None], 'tmytm':['1E+00',3,np.nan]})
    out=prepare_risk_free(d)
    assert np.isclose(out.RF.iloc[0], np.mean(np.expm1(np.array([1.,3.])/100*30/365)))
    assert out.attrs['diagnostics']['placeholder_rows_removed']==1
    d.loc[2,'tmytm']=1
    with pytest.raises(ValueError):prepare_risk_free(d)


def test_previous_month_weight_does_not_bridge_gap():
    d=pd.DataFrame({'permno':[1,1,1], 'mdate':pd.to_datetime(['2020-01-01','2020-03-01','2020-04-01']), 'me':[10,20,30]})
    w=previous_month_weights(d)
    assert w.isna().tolist()==[True,True,False] and w.iloc[2]==20


def test_independent_annual_inputs_at_june_and_consecutive_years():
    c=clean_crsp(crsp_rows(dates=('2019-12-31','2020-06-30','2020-07-31')))
    a=clean_compustat(accounts())
    p=attach_annual_accounts(link_crsp_compustat(c, clean_ccm(links())), a)
    # June monthly carrier has FY2018; the formation correctly uses independent FY2019.
    assert p.loc[p.mdate.eq('2020-06-01'),'fyear'].iloc[0]==2018
    measured=characteristic_panel(p,a)
    june=measured.loc[measured.date.eq('2020-06-01')].iloc[0]
    assert np.isclose(june.bm,53.) and np.isclose(june.op,45/53) and np.isclose(june.inv,.2)
    assert june.formation_eligible
    a=clean_compustat(accounts(years=(2017,2019)))
    assert pd.isna(characteristic_panel(p,a).loc[lambda x:x.date.eq('2020-06-01'),'inv'].iloc[0])


def test_fiscal_label_cannot_introduce_later_calendar_accounts():
    c=clean_crsp(crsp_rows(dates=('2019-12-31','2020-06-30')))
    a=accounts(years=(2019,));a['datadate']='2020-01-31';a=clean_compustat(a)
    p=attach_annual_accounts(link_crsp_compustat(c, clean_ccm(links())), a)
    m=characteristic_panel(p,a)
    assert m.loc[m.date.eq('2020-06-01'),['bm','op','inv']].isna().all().all()


def test_reference_size_median_and_july_june_labels():
    # AMEX size=2 lies between lower-order 50% cutoff=1 and NYSE median=3.
    rows=[]
    for date in pd.to_datetime(['2020-06-01','2020-07-01','2021-06-01']):
        for security, size, exchange in [(1,1,1),(2,5,1),(3,2,2)]:
            rows.append(dict(permno=security,date=date,ffyear=date.year if date.month>=7 else date.year-1,
                exchcd=exchange,me=size,bm=size,op=size,inv=size,formation_eligible=True))
    result=annual_ff5_assignments(pd.DataFrame(rows))
    held=result['panel'].loc[lambda d:d.date.ge('2020-07-01') & d.permno.eq(3)]
    assert held.me_portfolio.eq(1).all()
    assert result['breakpoints'].loc[lambda d:d.characteristic.eq('me'),'breakpoint'].eq(3).all()


def test_panel_validation_rejects_link_and_rf_errors():
    c=clean_crsp(crsp_rows());a=clean_compustat(accounts())
    p=attach_annual_accounts(link_crsp_compustat(c,clean_ccm(links())),a);p['RF']=.001
    assert validate_prepared_panel(p)['rows']==2
    p.loc[0,'RF']=np.nan
    with pytest.raises(ValueError,match='RF'):validate_prepared_panel(p)
    p['RF']=.001;p.loc[0,'linkenddt']=pd.Timestamp('2010-01-01')
    with pytest.raises(ValueError,match='CCM'):validate_prepared_panel(p)


def test_cache_requires_original_files_and_matching_hashes(tmp_path):
    pytest.importorskip('pyarrow')
    raw=tmp_path/'raw';raw.mkdir();processed=tmp_path/'processed'
    for name in SOURCE_FILES.values():(raw/name).write_text('synthetic original\n')
    panel=pd.DataFrame({'mdate':pd.to_datetime(['2020-01-01','2020-02-01']), 'permno':[1,1]})
    annual=accounts()
    with pytest.raises(FileNotFoundError,match='notebooks/00'):load_prepared_data(processed,raw)
    save_prepared_data(panel,annual,processed,raw,{'synthetic':True})
    result,_=load_prepared_data(processed,raw,start='2020-02-01')
    assert len(result)==1
    (raw/SOURCE_FILES['crsp']).write_text('changed original\n')
    with pytest.raises(ValueError,match='stale'):load_prepared_data(processed,raw)


def test_fiscal_label_cannot_reuse_an_expired_calendar_account():
    c=clean_crsp(crsp_rows(dates=('2020-12-31','2021-06-30')))
    a=accounts(years=(2020,));a['datadate']='2019-12-31';a=clean_compustat(a)
    p=attach_annual_accounts(link_crsp_compustat(c, clean_ccm(links(end='.E'))), a)
    m=characteristic_panel(p,a)
    assert m.loc[m.date.eq('2021-06-01'),['bm','op','inv']].isna().all().all()
