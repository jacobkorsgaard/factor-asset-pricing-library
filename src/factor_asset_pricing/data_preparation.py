"""Small, explicit CRSP–Compustat cleaning and historical-link calculations.

Inputs are DataFrames from original exports. There is no file I/O here. Rules
retain the reference replication, with ambiguity checks and explicit diagnostics.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .characteristics import adjusted_return, market_equity
from .wrds_data import ACCOUNTING_COLUMNS, REQUIRED_COLUMNS


def _require(data, columns):
    missing = set(columns) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")


def _numeric(values):
    text = values.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})
    converted = pd.to_numeric(text, errors="coerce")
    bad = text.notna() & converted.isna()
    if bad.any():
        raise ValueError(f"Unrecognized numeric values: {text.loc[bad].unique()[:5].tolist()}")
    if np.isinf(converted.to_numpy(dtype=float, na_value=np.nan)).any():
        raise ValueError("Infinite numeric input")
    return converted.astype(float)


def _integer(values):
    numeric = _numeric(values)
    if numeric.dropna().mod(1).ne(0).any():
        raise ValueError("Identifier/year must be integer valued")
    return numeric.astype("Int64")


def _gvkey(values):
    text = values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    if (~text.dropna().str.fullmatch(r"\d{1,6}")).any():
        raise ValueError("GVKEY must be a numeric company identifier")
    return text.str.zfill(6)


def clean_crsp(data: pd.DataFrame) -> pd.DataFrame:
    """Validate security months, decimal returns, and exchange/share eligibility.

    Keep negative price flags, missing returns and delisting-only observations.
    Recognized CRSP return flags/sentinels become missing, never zero. No
    delisting imputation or company-level market-cap aggregation is performed.
    """
    _require(data, REQUIRED_COLUMNS["crsp"])
    out = data[REQUIRED_COLUMNS["crsp"]].copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    out["mdate"] = out["date"].dt.to_period("M").dt.to_timestamp()
    for col in ["permno", "shrcd", "exchcd"]:
        out[col] = _integer(out[col])
    if out[["permno", "mdate"]].isna().any().any() or out.permno.le(0).any():
        raise ValueError("Missing/invalid CRSP security-month key")
    if out.duplicated(["permno", "mdate"]).any():
        raise ValueError("Duplicate CRSP security month; resolve the export before linking")
    for col in ["ret", "dlret"]:
        values = out[col].astype("string").str.strip().replace({c: pd.NA for c in ["A", "B", "C", "D", "E", "S", "T", "P"]})
        out[col] = _numeric(values).replace([-44, -55, -66, -77, -88, -99], np.nan)
        if out[col].dropna().lt(-1).any():
            raise ValueError(f"{col}: simple returns below -100%; check units/flags")
    for col in ["prc", "shrout"]:
        out[col] = _numeric(out[col])
    # Filter records, not entire securities: historical codes may change.
    out = out.loc[out.exchcd.isin([1, 2, 3]) & out.shrcd.isin([10, 11])].copy()
    out["retadj"] = adjusted_return(out.ret, out.dlret)
    out["me"] = market_equity(out.prc, out.shrout)
    out.attrs["diagnostics"] = {"raw_rows": len(data), "eligible_rows": len(out),
        "missing_adjusted_returns": int(out.retadj.isna().sum()),
        "delisting_only_rows": int((out.ret.isna() & out.dlret.notna()).sum()),
        "negative_price_flags": int(out.prc.lt(0).sum())}
    return out.sort_values(["permno", "mdate"]).reset_index(drop=True)


def clean_compustat(data: pd.DataFrame) -> pd.DataFrame:
    """Select industrial, standard, consolidated USD accounts; deduplicate years.

    Do not filter COSTAT to active firms. Keep latest datadate within GVKEY/FYEAR;
    conflicting statements at the same final date raise instead of arbitrary
    selection. Investment history is kept separate from the monthly carriers.
    """
    _require(data, REQUIRED_COLUMNS["compustat"])
    out = data.copy()
    filters = {"indfmt": "INDL", "datafmt": "STD", "consol": "C", "curcd": "USD"}
    present = {key: val for key, val in filters.items() if key in out}
    for key, value in present.items():
        out = out.loc[out[key].astype("string").str.strip().eq(value)].copy()
    out = out[REQUIRED_COLUMNS["compustat"]].copy()
    out["gvkey"] = _gvkey(out.gvkey)
    out["datadate"] = pd.to_datetime(out.datadate, errors="raise")
    out["fyear"] = _integer(out.fyear)
    if out[["gvkey", "datadate", "fyear"]].isna().any().any():
        raise ValueError("Missing annual accounting key")
    for col in ACCOUNTING_COLUMNS:
        out[col] = _numeric(out[col])
    out = out.drop_duplicates()
    latest = out.groupby(["gvkey", "fyear"], observed=True).datadate.transform("max")
    out = out.loc[out.datadate.eq(latest)].copy()
    if out.duplicated(["gvkey", "fyear"]).any():
        raise ValueError("Conflicting latest Compustat company-year records")
    # Explicit reference convention; these are assumed holding dates, not filings.
    year = out.datadate.dt.year
    out["available_from"] = pd.to_datetime(dict(year=year + 1, month=7, day=1))
    out["available_until"] = pd.to_datetime(dict(year=year + 2, month=6, day=1))
    out["formation_date"] = pd.to_datetime(dict(year=out.fyear.astype(int) + 1, month=6, day=30))
    out.attrs["diagnostics"] = {"raw_rows": len(data), "annual_rows": len(out),
        "excluded_or_duplicate_rows": len(data) - len(out),
        "format_filters_present": list(present),
        "format_filters_absent": sorted(set(filters) - set(present)),
        "fiscal_calendar_mismatches": int(out.fyear.ne(out.datadate.dt.year).sum())}
    return out.sort_values(["gvkey", "fyear"]).reset_index(drop=True)


def clean_ccm(data: pd.DataFrame) -> pd.DataFrame:
    """Retain reference LU/LC/LN/LS and P/C links, including historical endpoints."""
    _require(data, REQUIRED_COLUMNS["ccm"])
    out = data[REQUIRED_COLUMNS["ccm"]].copy()
    for col in ["linkprim", "linktype"]:
        out[col] = out[col].astype("string").str.strip().str.upper()
    out = out.loc[out.linkprim.isin(["P", "C"]) & out.linktype.isin(["LU", "LC", "LN", "LS"])].copy()
    out["gvkey"] = _gvkey(out.gvkey)
    out["permno"] = _integer(out.pop("lpermno"))
    # WRDS .B/.E (or blank) are open intervals, not invalid dated links.
    start = out.linkdt.astype("string").str.strip().replace({".B": pd.NA, ".": pd.NA})
    end = out.linkenddt.astype("string").str.strip().replace({".E": pd.NA, "E": pd.NA, ".": pd.NA})
    out["linkdt"] = pd.to_datetime(start, errors="raise").fillna(pd.Timestamp("1900-01-01"))
    out["linkenddt"] = pd.to_datetime(end, errors="raise").fillna(pd.Timestamp("2262-04-11"))
    if out[["gvkey", "permno"]].isna().any().any() or out.permno.le(0).any():
        raise ValueError("Invalid eligible CCM identifiers")
    if out.linkdt.gt(out.linkenddt).any():
        raise ValueError("CCM start follows end")
    out = out.drop_duplicates().reset_index(drop=True)
    out.attrs["diagnostics"] = {"raw_rows": len(data), "eligible_links": len(out)}
    return out


def link_crsp_compustat(crsp: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Apply CCM intervals at month start, then reference primary/type priorities.

    Month-start evaluation deliberately preserves the reference boundary rule.
    Prefer P over C, LU over LC over LN over LS, then latest start. Equally
    preferred conflicting GVKEYs raise. Unlinked stocks are excluded, as in
    the reference, including from this exercise's market proxy.
    """
    _require(crsp, ["permno", "mdate"])
    _require(links, ["permno", "gvkey", "linkdt", "linkenddt", "linkprim", "linktype"])
    # Build candidates with keys only, avoiding replication of accounting/price fields.
    candidates = crsp[["permno", "mdate"]].merge(links, on="permno", how="inner")
    candidates = candidates.loc[candidates.mdate.ge(candidates.linkdt) & candidates.mdate.le(candidates.linkenddt)].copy()
    candidates["primary_rank"] = candidates.linkprim.map({"P": 1, "C": 2})
    candidates["type_rank"] = candidates.linktype.map({"LU": 1, "LC": 2, "LN": 3, "LS": 4})
    rank_keys = ["permno", "mdate", "primary_rank", "type_rank", "linkdt"]
    conflicts = candidates.groupby(rank_keys, observed=True).gvkey.nunique().gt(1)
    if conflicts.any():
        raise ValueError("Ambiguous CCM links with identical priority/date; resolve the source")
    overlapping = int(candidates.duplicated(["permno", "mdate"]).sum())
    candidates = candidates.sort_values(rank_keys, ascending=[True, True, True, True, False]).drop_duplicates(["permno", "mdate"])
    selected = candidates.drop(columns=["primary_rank", "type_rank"])
    result = crsp.merge(selected, on=["permno", "mdate"], how="inner", validate="one_to_one")
    result.attrs["diagnostics"] = {"eligible_crsp_rows": len(crsp), "linked_rows": len(result),
        "unlinked_rows": len(crsp) - len(result), "overlap_candidates_resolved": overlapping}
    return result.sort_values(["permno", "mdate"]).reset_index(drop=True)


def attach_annual_accounts(linked: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    """Attach accounts only within their assumed July–June availability window."""
    # Latest statement within a calendar availability year; differing FYEAR dates
    # are retained in the independent annual table for investment diagnostics.
    accounts = annual.sort_values(["gvkey", "available_from", "datadate"])
    accounts = accounts.drop_duplicates(["gvkey", "available_from"], keep="last")
    columns = ["gvkey", "datadate", "fyear", "available_from", "available_until", *ACCOUNTING_COLUMNS]
    out = pd.merge_asof(linked.sort_values("mdate"), accounts[columns].sort_values("available_from"),
                        left_on="mdate", right_on="available_from", by="gvkey", direction="backward")
    expired = out.available_until.notna() & out.mdate.gt(out.available_until)
    out.loc[expired, [c for c in columns if c != "gvkey"]] = np.nan
    assert not (out.available_from.notna() & out.mdate.lt(out.available_from)).any()
    out.attrs["diagnostics"] = {"rows_with_accounts": int(out.datadate.notna().sum()),
        "expired_carriers_removed": int(expired.sum())}
    return out.sort_values(["permno", "mdate"]).reset_index(drop=True)


def prepare_risk_free(data: pd.DataFrame) -> pd.DataFrame:
    """Reference Treasury conversion: exp((annual yield/100)*30/365)−1."""
    _require(data, ["mcaldt", "tmytm"])
    dates = pd.to_datetime(data.mcaldt, errors="raise")
    values = _numeric(data.tmytm)
    if (dates.isna() & values.notna()).any():
        raise ValueError("Treasury yield lacks an observation date")
    out = pd.DataFrame({"mdate": dates.dt.to_period("M").dt.to_timestamp(),
                        "RF": np.expm1(values / 100 * 30 / 365)})
    # The export includes instrument placeholders with neither date nor yield.
    out = out.loc[dates.notna()].groupby("mdate", as_index=False).RF.mean()
    if out.RF.isna().any():
        raise ValueError("Missing monthly Treasury rate")
    out.attrs["diagnostics"] = {"placeholder_rows_removed": int(dates.isna().sum()), "monthly_rates": len(out)}
    return out


def validate_prepared_panel(panel: pd.DataFrame) -> dict:
    """Check unique linked keys, link windows, accounting timing, and RF coverage."""
    _require(panel, ["permno", "gvkey", "mdate", "linkdt", "linkenddt", "available_from", "available_until", "RF", "retadj", "me"])
    if panel[["permno", "gvkey", "mdate"]].isna().any().any() or panel.duplicated(["permno", "mdate"]).any():
        raise ValueError("Panel keys missing or duplicated")
    if not panel.mdate.eq(panel.mdate.dt.to_period("M").dt.to_timestamp()).all():
        raise ValueError("Panel dates must be month starts")
    if (panel.mdate.lt(panel.linkdt) | panel.mdate.gt(panel.linkenddt)).any():
        raise ValueError("Observations outside historical CCM intervals")
    has_accounts = panel.available_from.notna()
    if (panel.loc[has_accounts, "mdate"].lt(panel.loc[has_accounts, "available_from"]) |
            panel.loc[has_accounts, "mdate"].gt(panel.loc[has_accounts, "available_until"])).any():
        raise ValueError("Accounting carrier outside availability window")
    if panel.RF.isna().any():
        raise ValueError("Security-month panel lacks monthly RF coverage")
    return {"rows": len(panel), "securities": panel.permno.nunique(), "companies": panel.gvkey.nunique(),
        "start": str(panel.mdate.min().date()), "end": str(panel.mdate.max().date()),
        "linked_share": float(panel.gvkey.notna().mean()), "missing_returns": int(panel.retadj.isna().sum()),
        "missing_market_equity": int(panel.me.isna().sum())}


def previous_month_weights(panel: pd.DataFrame) -> pd.Series:
    """Beginning-month ME; do not carry values across absent calendar months."""
    _require(panel, ["permno", "mdate", "me"])
    if panel.duplicated(["permno", "mdate"]).any():
        raise ValueError("Duplicate security months")
    ordered = panel.sort_values(["permno", "mdate"])
    lag = ordered.groupby("permno", observed=True).me.shift(1)
    month = ordered.mdate.dt.to_period("M").astype("int64")
    prior = month.groupby(ordered.permno, observed=True).shift(1)
    return lag.where(month.sub(prior).eq(1) & lag.gt(0)).reindex(panel.index)
