"""Standard firm characteristics used in empirical asset pricing.

This module separates economic definitions from portfolio formation.  The
small functions are useful with any appropriately aligned data, while
``fama_french_characteristics`` reproduces the annual timing conventions used
in the companion Fama--French five-factor replication.

The module assumes inputs have already been cleaned and linked.  It deliberately
does not download data, resolve CRSP--Compustat links, or provide a generic data-
cleaning framework.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# =============================================================================
# 1. Return and market-equity characteristics
# =============================================================================
def adjusted_return(returns: pd.Series, delisting_returns: pd.Series) -> pd.Series:
    """Combine ordinary and delisting returns.

    When both exist, the total return is ``(1 + ret) * (1 + dlret) - 1``.
    When only one exists, that return is retained.  This mirrors the CRSP
    convention used in the reference replication and avoids dropping the final
    delisting payoff.
    """
    ret = pd.Series(returns, copy=False)
    dlret = pd.Series(delisting_returns, copy=False).reindex(ret.index)
    return pd.Series(
        np.select(
            [ret.notna() & dlret.notna(), ret.notna(), dlret.notna()],
            [(1 + ret) * (1 + dlret) - 1, ret, dlret],
            default=np.nan,
        ),
        index=ret.index,
        dtype=float,
    )


def market_equity(price: pd.Series, shares_outstanding: pd.Series) -> pd.Series:
    """Calculate equity market capitalization as absolute price times shares.

    CRSP sometimes uses the sign of ``PRC`` to flag a bid/ask midpoint, so the
    sign is not economically meaningful for market capitalization.  Nonpositive
    shares outstanding produce missing market equity.
    """
    price = pd.Series(price, copy=False).abs()
    shares = pd.Series(shares_outstanding, copy=False).reindex(price.index)
    return (price * shares).where(price.notna() & shares.gt(0))


# =============================================================================
# 2. Accounting characteristics
# =============================================================================
def book_equity(
    shareholders_equity: pd.Series,
    deferred_taxes: pd.Series,
    preferred_redemption: pd.Series,
    preferred_liquidation: pd.Series,
    preferred_stock: pd.Series,
) -> pd.Series:
    """Construct Fama--French book equity.

    Preferred stock uses redemption value first, liquidation value second, and
    carrying value last. Missing deferred taxes and preferred stock are treated
    as zero. Nonpositive book equity is set to missing before portfolio sorts.
    """
    seq = pd.Series(shareholders_equity, copy=False)
    txditc = pd.Series(deferred_taxes, copy=False).reindex(seq.index)
    preferred = (
        pd.Series(preferred_redemption, copy=False).reindex(seq.index)
        .combine_first(pd.Series(preferred_liquidation, copy=False).reindex(seq.index))
        .combine_first(pd.Series(preferred_stock, copy=False).reindex(seq.index))
        .fillna(0)
    )
    result = seq + txditc.fillna(0) - preferred
    return result.where(seq.notna() & result.gt(0))


def operating_profitability(
    revenue: pd.Series,
    cost_of_goods_sold: pd.Series,
    selling_general_admin: pd.Series,
    interest_expense: pd.Series,
    book_equity_values: pd.Series,
) -> pd.Series:
    """Fama--French operating profitability scaled by book equity.

    ``(revenue - COGS - SG&A - interest expense) / book equity`` is calculated
    when revenue, COGS, and positive book equity are available. Missing SG&A and
    interest expense are treated as zero, matching the reference replication.
    """
    revenue = pd.Series(revenue, copy=False)
    cogs = pd.Series(cost_of_goods_sold, copy=False).reindex(revenue.index)
    xsga = pd.Series(selling_general_admin, copy=False).reindex(revenue.index)
    xint = pd.Series(interest_expense, copy=False).reindex(revenue.index)
    be = pd.Series(book_equity_values, copy=False).reindex(revenue.index)
    numerator = revenue - cogs - xsga.fillna(0) - xint.fillna(0)
    return (numerator / be).where(revenue.notna() & cogs.notna() & be.gt(0))


def investment(total_assets: pd.Series, *, group=None) -> pd.Series:
    """Asset growth, ``(AT_t - AT_{t-1}) / AT_{t-1}``.

    Supply ``group`` (for example, GVKEY) when the series contains multiple
    firms. Input rows must already be ordered chronologically within firm.
    """
    assets = pd.Series(total_assets, copy=False)
    lagged = assets.groupby(group, observed=True).shift(1) if group is not None else assets.shift(1)
    return ((assets - lagged) / lagged).where(assets.notna() & lagged.gt(0))


def book_to_market(book_equity_values: pd.Series, december_market_equity: pd.Series) -> pd.Series:
    """Book equity divided by positive prior-December market equity."""
    be = pd.Series(book_equity_values, copy=False)
    me = pd.Series(december_market_equity, copy=False).reindex(be.index)
    return (be / me).where(be.notna() & me.gt(0))


# =============================================================================
# 3. Fama--French timing and combined construction
# =============================================================================
def fama_french_characteristics(
    panel: pd.DataFrame,
    *,
    id_col: str = "permno",
    company_col: str = "gvkey",
    date_col: str = "date",
    fiscal_year_col: str = "fyear",
    accounting_date_col: str = "datadate",
    market_equity_scale: float = 1000.0,
) -> pd.DataFrame:
    """Add standard Fama--French return, size, value, OP, and investment fields.

    Expected raw columns are ``ret``, ``dlret``, ``prc``, ``shrout``, ``seq``,
    ``txditc``, ``pstkrv``, ``pstkl``, ``pstk``, ``revt``, ``cogs``, ``xsga``,
    ``xint``, and ``at``. The returned fields are:

    - ``retadj``: return including delisting returns;
    - ``me``: market equity in the input price/share units;
    - ``book_equity``: positive accounting book equity;
    - ``op``: operating profitability;
    - ``inv``: annual asset growth;
    - ``bm``: book-to-market using prior-December market equity;
    - ``ffyear``: July-to-June portfolio holding year;
    - ``has_dec`` and ``has_june``: formation-history indicators.

    Fiscal-year t information is assigned to calendar formation year t+1.
    December market equity from t-1 is used for formation year t. By default it
    is divided by 1,000 because CRSP ``PRC * SHROUT`` is in thousands of dollars
    while Compustat book equity is commonly in millions. Set
    ``market_equity_scale=1`` when the input units already match. This function
    expects an already linked, point-in-time CRSP--Compustat-style panel.
    """
    data = panel.copy()
    data[date_col] = pd.to_datetime(data[date_col])
    data["year"] = data[date_col].dt.year
    data["month"] = data[date_col].dt.month
    data["ffyear"] = np.where(data["month"].ge(7), data["year"], data["year"] - 1)

    data["retadj"] = adjusted_return(data["ret"], data["dlret"])
    data["me"] = market_equity(data["prc"], data["shrout"])
    data["book_equity"] = book_equity(
        data["seq"], data["txditc"], data["pstkrv"], data["pstkl"], data["pstk"]
    )

    annual_cols = [
        company_col, fiscal_year_col, accounting_date_col, "revt", "cogs",
        "xsga", "xint", "book_equity", "at",
    ]
    annual = (
        data.loc[data[company_col].notna() & data[fiscal_year_col].notna(), annual_cols]
        .sort_values([company_col, fiscal_year_col, accounting_date_col])
        .drop_duplicates([company_col, fiscal_year_col], keep="last")
    )
    annual["op"] = operating_profitability(
        annual["revt"], annual["cogs"], annual["xsga"], annual["xint"], annual["book_equity"]
    )
    annual = annual.sort_values([company_col, fiscal_year_col])
    annual["inv"] = investment(annual["at"], group=annual[company_col])
    annual["signal_year"] = annual[fiscal_year_col].astype("Int64") + 1
    attributes = annual[[company_col, "signal_year", "book_equity", "op", "inv"]].rename(
        columns={"book_equity": "book_equity_ff"}
    )

    data["signal_year"] = data["year"]
    data = data.merge(attributes, on=[company_col, "signal_year"], how="left")
    december = data.loc[data["month"].eq(12), [id_col, "year", "me"]].copy()
    december["signal_year"] = december["year"] + 1
    december["me_dec"] = december["me"] / market_equity_scale
    december = december[[id_col, "signal_year", "me_dec"]].drop_duplicates(
        [id_col, "signal_year"], keep="last"
    )
    data = data.merge(december, on=[id_col, "signal_year"], how="left")
    data["bm"] = book_to_market(data["book_equity_ff"], data["me_dec"])

    december_presence = data.loc[data["month"].eq(12), [id_col, "year"]].copy()
    december_presence["ffyear"] = december_presence["year"] + 1
    december_presence["has_dec"] = True
    june_presence = data.loc[data["month"].eq(6), [id_col, "year"]].copy()
    june_presence["ffyear"] = june_presence["year"]
    june_presence["has_june"] = True
    data = data.merge(
        december_presence[[id_col, "ffyear", "has_dec"]].drop_duplicates(),
        on=[id_col, "ffyear"], how="left",
    ).merge(
        june_presence[[id_col, "ffyear", "has_june"]].drop_duplicates(),
        on=[id_col, "ffyear"], how="left",
    )
    data[["has_dec", "has_june"]] = data[["has_dec", "has_june"]].fillna(False)
    return data.drop(columns="signal_year").sort_values([id_col, date_col]).reset_index(drop=True)
