"""Read local WRDS exports and reproducible local caches, without financial logic."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import tempfile

import pandas as pd

SOURCE_FILES = {
    "crsp": "CRSP-1950_01-2024_12.csv",
    "compustat": "Compustat-1950_06 - 2024_12.csv",
    "ccm": "Merger CRISPxCompustat.csv",
    "risk_free": "CRSP - Riskfree - 1950_01_01 - 2024_12_31.csv",
}
ACCOUNTING_COLUMNS = ["at", "pstk", "pstkl", "pstkrv", "seq", "txditc", "cogs", "revt", "xint", "xsga"]
REQUIRED_COLUMNS = {
    "crsp": ["permno", "date", "shrcd", "exchcd", "ret", "dlret", "prc", "shrout"],
    "compustat": ["gvkey", "datadate", "fyear", *ACCOUNTING_COLUMNS],
    "ccm": ["gvkey", "linkprim", "linktype", "lpermno", "linkdt", "linkenddt"],
    "risk_free": ["mcaldt", "tmytm"],
}
FORMAT_COLUMNS = ["indfmt", "datafmt", "consol", "curcd", "costat"]
CACHE_VERSION = 1


def _name(value):
    value = re.sub(r"\\[A-Za-z]+\d*\s*", "", value)
    return re.sub(r"[^a-z0-9_]+", "", value.lower())


def read_wrds_export(path: str | Path, required_columns: list[str]) -> pd.DataFrame:
    """Read plain CSV or the numeric RTF-wrapped exports used in this project.

    Strip only RTF wrapper lines/controls and row terminators in a temporary
    stream; original bytes are never changed. This is not a general RTF parser.
    Required column names are case insensitive; GVKEY remains a string. Other
    columns, including statement-format filters, remain available to cleaners.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Original WRDS export required: {path}")
    with path.open(encoding="utf-8-sig") as handle:
        wrapped = handle.readline().startswith(r"{\rtf")
        handle.seek(0)
        header_found = False
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as stream:
            for line in handle:
                candidate = line.rstrip()
                if wrapped:
                    candidate = candidate.rstrip("\\}")
                if not header_found:
                    names = [_name(v) for v in next(csv.reader([candidate]))]
                    if set(required_columns).issubset(names):
                        if len(names) != len(set(names)):
                            raise ValueError("Duplicate normalized WRDS columns")
                        stream.write(",".join(names) + "\n")
                        header_found = True
                    continue
                if candidate and candidate != "}":
                    stream.write(candidate + "\n")
            if not header_found:
                raise ValueError(f"{path.name}: required header missing: {required_columns}")
            stream.seek(0)
            data = pd.read_csv(stream, low_memory=False, dtype={"gvkey": "string"})
    data.attrs.update(source_file=str(path), rows_read=len(data), rtf_wrapped=wrapped)
    return data


def read_wrds_source(raw_dir: str | Path, dataset: str) -> pd.DataFrame:
    """Read one of the four registered original exports, with no live connection."""
    if dataset not in SOURCE_FILES:
        raise ValueError(f"Unknown WRDS dataset: {dataset}")
    return read_wrds_export(Path(raw_dir) / SOURCE_FILES[dataset], REQUIRED_COLUMNS[dataset])


def source_manifest(raw_dir: str | Path) -> dict:
    """Hash original bytes in bounded chunks for cache/provenance checks."""
    result = {}
    for dataset, filename in SOURCE_FILES.items():
        path = Path(raw_dir) / filename
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result[dataset] = {"file": filename, "sha256": digest.hexdigest(), "bytes": path.stat().st_size}
    return result


def save_prepared_data(panel, annual, processed_dir, raw_dir, diagnostics):
    """Persist local restricted Parquet intermediates plus a source-hash manifest.

    Both cache tables are necessary: annual accounts must be available separately
    for June formation, rather than recovered retrospectively from July carriers.
    """
    directory = Path(processed_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / "crsp_compustat_monthly.parquet", directory / "compustat_annual.parquet"]
    # Invalidate a previous manifest before replacing either table.
    manifest_path = directory / "wrds_preparation.json"
    manifest_path.unlink(missing_ok=True)
    for frame, path in zip([panel, annual], paths):
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".parquet", delete=False) as temp:
            temporary = Path(temp.name)
        try:
            frame.to_parquet(temporary, index=False)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    manifest = {"version": CACHE_VERSION, "sources": source_manifest(raw_dir), "diagnostics": diagnostics}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def load_prepared_data(processed_dir: str | Path, raw_dir: str | Path, *, start=None, end=None):
    """Load local preparation output only if its original-source hashes match.

    Run notebook 00 when absent/stale. No fallback to a companion repository.
    Optional month-start bounds limit security-panel reads; annual accounts are
    returned independently so fiscal-year histories are never truncated by them.
    """
    directory = Path(processed_dir)
    manifest_path = directory / "wrds_preparation.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Run notebooks/00_crsp_compustat_data_preparation.ipynb from original WRDS exports first")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("version") != CACHE_VERSION or manifest.get("sources") != source_manifest(raw_dir):
        raise ValueError("WRDS cache is stale; rerun notebook 00 from original exports")
    filters = []
    if start is not None:
        filters.append(("mdate", ">=", pd.Timestamp(start)))
    if end is not None:
        filters.append(("mdate", "<=", pd.Timestamp(end)))
    panel = pd.read_parquet(directory / "crsp_compustat_monthly.parquet", filters=filters or None)
    annual = pd.read_parquet(directory / "compustat_annual.parquet")
    return panel, annual
