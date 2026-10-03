"""Generic validation of constructed returns against external benchmarks."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .asset_pricing_tests import time_series_regression


# =============================================================================
# 1. Return-series and factor-panel validation
# =============================================================================
def validate_return_series(
    constructed: pd.Series,
    reference: pd.Series,
    *,
    hac_lags: int = 12,
) -> pd.Series:
    """Compare one constructed return series with an aligned benchmark series."""
    sample = pd.concat(
        [constructed.rename("constructed"), reference.rename("reference")], axis=1
    ).dropna()
    if sample.empty:
        raise ValueError("constructed and reference returns have no common observations")
    fit = time_series_regression(
        sample["constructed"], sample[["reference"]], cov_type="HAC", hac_lags=hac_lags
    )
    return pd.Series(
        {
            "observations": len(sample),
            "start": sample.index.min(),
            "end": sample.index.max(),
            "mean_constructed": sample["constructed"].mean(),
            "mean_reference": sample["reference"].mean(),
            "mean_difference": (sample["constructed"] - sample["reference"]).mean(),
            "correlation": sample["constructed"].corr(sample["reference"]),
            "alpha": fit.params["const"],
            "alpha_standard_error": fit.bse["const"],
            "alpha_t_statistic": fit.tvalues["const"],
            "alpha_p_value": fit.pvalues["const"],
            "loading": fit.params["reference"],
            "loading_standard_error": fit.bse["reference"],
            "r_squared": fit.rsquared,
            "adjusted_r_squared": fit.rsquared_adj,
        }
    )


def validate_factor_returns(
    constructed: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    factors: Sequence[str] | None = None,
    hac_lags: int = 12,
) -> pd.DataFrame:
    """Validate matching factor columns from two date-indexed return panels."""
    names = list(factors) if factors is not None else [
        name for name in constructed.columns if name in reference.columns
    ]
    if not names:
        raise ValueError("constructed and reference panels contain no requested common factors")
    rows = []
    for name in names:
        if name not in constructed or name not in reference:
            raise KeyError(name)
        summary = validate_return_series(
            constructed[name], reference[name], hac_lags=hac_lags
        ).to_dict()
        rows.append({"factor": name, **summary})
    return pd.DataFrame(rows).set_index("factor")


# =============================================================================
# 2. Grouped portfolio validation
# =============================================================================
def validate_portfolios(
    constructed: pd.DataFrame,
    reference: pd.DataFrame,
    *,
    portfolio_cols: str | Sequence[str],
    date_col: str = "date",
    constructed_col: str = "ret",
    reference_col: str = "ret",
    hac_lags: int = 12,
) -> pd.DataFrame:
    """Validate matching portfolio returns using arbitrary portfolio keys."""
    groups = [portfolio_cols] if isinstance(portfolio_cols, str) else list(portfolio_cols)
    keys = [date_col, *groups]
    comparison = constructed[[*keys, constructed_col]].rename(
        columns={constructed_col: "constructed"}
    ).merge(
        reference[[*keys, reference_col]].rename(columns={reference_col: "reference"}),
        on=keys,
        how="inner",
    )
    rows = []
    for group_key, sample in comparison.groupby(groups, observed=True):
        group_key = group_key if isinstance(group_key, tuple) else (group_key,)
        indexed = sample.set_index(date_col).sort_index()
        summary = validate_return_series(
            indexed["constructed"], indexed["reference"], hac_lags=hac_lags
        ).to_dict()
        rows.append({**dict(zip(groups, group_key)), **summary})
    return pd.DataFrame(rows)
