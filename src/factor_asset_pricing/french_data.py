"""Original Kenneth French CSV/ZIP ingestion; no financial calculations.

Returns are decimals. Monthly dates are calendar month starts; daily dates
are trading dates. Local originals take precedence and are never rewritten.
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
import re
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd

BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
# Dataset key: original filename stem. Frequency is selected explicitly below.
SOURCES = {
    "ff3": "F-F_Research_Data_Factors",
    "ff5": "F-F_Research_Data_5_Factors_2x3",
    "momentum": "F-F_Momentum_Factor",
    "size": "Portfolios_Formed_on_ME",
    "momentum_deciles": "10_Portfolios_Prior_12_2",
    "size_bm": "25_Portfolios_5x5",
    "size_op": "25_Portfolios_ME_OP_5x5",
    "size_inv": "25_Portfolios_ME_INV_5x5",
    "size_bm_op": "32_Portfolios_ME_BEME_OP_2x4x4",
    "size_bm_inv": "32_Portfolios_ME_BEME_INV_2x4x4",
    "size_op_inv": "32_Portfolios_ME_OP_INV_2x4x4",
}
_FACTOR_COLUMNS = {"ff3": ["Mkt-RF", "SMB", "HML", "RF"],
                   "ff5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
                   "momentum": ["Mom"]}


def source_url(dataset: str, frequency: str = "monthly") -> str:
    """Official download URL for a supported dataset and frequency."""
    if dataset not in SOURCES:
        raise ValueError(f"Unknown French dataset: {dataset}")
    if frequency not in {"monthly", "daily"}:
        raise ValueError("frequency must be monthly or daily")
    if frequency == "daily" and dataset not in _FACTOR_COLUMNS:
        raise ValueError("Daily ingestion is supported for factors only")
    suffix = "_daily" if frequency == "daily" else ""
    return BASE_URL + SOURCES[dataset] + suffix + "_CSV.zip"


def _csv_text(payload: bytes) -> str:
    if payload.startswith(b"PK"):
        with ZipFile(io.BytesIO(payload)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith('.csv')]
            if len(names) != 1:
                raise ValueError("Expected one CSV member in French archive")
            payload = archive.read(names[0])
    return payload.decode("utf-8-sig")


def _parse(payload: bytes, dataset: str, frequency: str) -> pd.DataFrame:
    lines = _csv_text(payload).splitlines()
    start = 0
    if dataset not in _FACTOR_COLUMNS:
        start = next((i + 1 for i, line in enumerate(lines)
                      if re.search(r"(?:Average )?Value Weight(?:ed)? Returns\s*--\s*Monthly", line, re.I)), -1)
        if start < 0:
            raise ValueError("Missing value-weighted monthly return section")
    digits = 8 if frequency == "daily" else 6
    pattern = re.compile(rf"^\s*\d{{{digits}}}\s*,")
    first = next((i for i in range(start, len(lines)) if pattern.match(lines[i])), None)
    if first is None:
        raise ValueError(f"No {frequency} returns in source")
    header = [s.strip() for s in next(csv.reader([lines[first - 1]]))]
    if not header or header[0] or len(set(header[1:])) != len(header) - 1:
        raise ValueError("Invalid French return header")
    required = _FACTOR_COLUMNS.get(dataset)
    if required is not None and header[1:] != required:
        raise ValueError(f"Unexpected factor columns: {header[1:]}; expected {required}")
    rows = []
    for line in lines[first:]:
        if not pattern.match(line):
            break  # Annual returns, equal weights, counts, and characteristics are excluded.
        fields = next(csv.reader([line]))
        if len(fields) != len(header):
            raise ValueError("Return row does not match header")
        rows.append(fields)
    frame = pd.DataFrame(rows, columns=["date", *header[1:]])
    dates = pd.to_datetime(frame.pop("date").str.strip(),
                           format="%Y%m%d" if frequency == "daily" else "%Y%m", errors="raise")
    frame = frame.apply(pd.to_numeric, errors="raise").replace([-99.99, -999], np.nan) / 100
    frame.index = pd.DatetimeIndex(dates, name="date")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("French dates must be unique and increasing")
    if not np.isfinite(frame.to_numpy()[frame.notna().to_numpy()]).all():
        raise ValueError("Nonfinite French returns")
    if frequency == "monthly":
        expected = pd.date_range(frame.index[0], frame.index[-1], freq="MS")
        if not frame.index.equals(expected.rename("date")):
            raise ValueError("Missing calendar months in French source")
    if required is not None:
        return frame.rename(columns={"Mkt-RF": "MKT", "Mom": "MOM"})
    if dataset.startswith("size_"):
        if dataset in {"size_bm", "size_op", "size_inv"}:
            labels = [f"S{s}C{c}" for s in range(1, 6) for c in range(1, 6)]
            characteristics = {"size_bm": ["BM"], "size_op": ["OP"], "size_inv": ["INV"]}[dataset]
        else:
            labels = [f"{s}-{a}-{b}" for s in ["S", "B"] for a in range(1, 5) for b in range(1, 5)]
            characteristics = {"size_bm_op": ["BM", "OP"], "size_bm_inv": ["BM", "INV"], "size_op_inv": ["OP", "INV"]}[dataset]
        if len(frame.columns) != len(labels) or any(
                not all(char in name for char in characteristics) for name in frame.columns):
            raise ValueError("Unexpected characteristic portfolio columns")
        size_count, rank_count = (5, 5) if len(labels) == 25 else (2, 4)
        canonical = []
        for name in frame.columns:
            name = name.replace("SMALL", "ME1").replace("BIG", f"ME{size_count}")
            for char in characteristics:
                name = name.replace(f"Lo{char}", f"{char}1").replace(f"Hi{char}", f"{char}{rank_count}")
            canonical.append(name)
        expected = [f"ME{s} {characteristics[0]}{a}" +
                    (f" {characteristics[1]}{b}" if len(characteristics) == 2 else "")
                    for s in range(1, size_count + 1)
                    for a in range(1, rank_count + 1)
                    for b in (range(1, rank_count + 1) if len(characteristics) == 2 else [1])]
        if canonical != expected:
            raise ValueError("Unexpected portfolio order or rank labels")
        # French publishes size-major, then first-characteristic-major order.
        frame.columns = labels
    elif dataset == "momentum_deciles":
        if list(frame.columns) != ["Lo PRIOR", *[f"PRIOR {i}" for i in range(2, 10)], "Hi PRIOR"]:
            raise ValueError("Unexpected momentum decile columns")
        frame.columns = [f"P{i}" for i in range(1, 11)]
    elif dataset == "size":
        columns = ["Lo 20", "Qnt 2", "Qnt 3", "Qnt 4", "Hi 20"]
        if not set(columns).issubset(frame.columns):
            raise ValueError("Missing size quintile columns")
        frame = frame[columns].copy()
        frame.columns = ["Small", "2", "3", "4", "Big"]
    return frame


def load_french(dataset: str, raw_dir: str | Path, *, frequency: str = "monthly",
                download: bool = True) -> pd.DataFrame:
    """Load original CSV or ZIP, downloading an absent source if allowed.

    Downloads preserve the ZIP bytes exactly, validate before writing, and use
    a temporary sibling for atomic publication. Malformed local files raise;
    they are never replaced silently. Set download=False for offline runs.
    Source path, URL and SHA-256 are attached as DataFrame attrs.
    """
    url = source_url(dataset, frequency)
    directory = Path(raw_dir)
    stem = SOURCES[dataset] + ("_daily" if frequency == "daily" else "")
    candidates = [directory / (stem + ".csv"), directory / (stem + ".CSV"),
                  directory / (stem + "_CSV.zip")]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        if not download:
            raise FileNotFoundError(f"Missing French source {stem}; obtain {url} in {directory}")
        with urlopen(url, timeout=60) as response:
            payload = response.read()
        frame = _parse(payload, dataset, frequency)
        directory.mkdir(parents=True, exist_ok=True)
        path = candidates[-1]
        # Exclusive unique temporary files prevent incomplete originals on failure.
        import tempfile
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".download", delete=False) as temp:
            temporary = Path(temp.name)
            temp.write(payload)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    else:
        payload = path.read_bytes()
        frame = _parse(payload, dataset, frequency)
    frame.attrs.update(source_file=str(path), source_url=url,
                       sha256=hashlib.sha256(payload).hexdigest(), frequency=frequency,
                       units="decimal", source_header=_csv_text(payload).splitlines()[0])
    return frame


def sample_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Report observed coverage and missing values per column, without dropping rows."""
    return pd.DataFrame({name: {"start": s.first_valid_index(), "end": s.last_valid_index(),
                               "observations": int(s.notna().sum()), "missing": int(s.isna().sum())}
                         for name, s in frame.items()}).T
