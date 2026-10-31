"""Batch audit of manually obtained B3 annual archives; engineering QA only.

Never downloads data, touches a 2026 lockbox, adjusts corporate actions,
calculates returns or writes price histories to GitHub. Annual COTAHIST archives
stay on the user's local computer. This report is metadata-only.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from .b3_cotahist import inspect_archive

_NAME = re.compile(r"COTAHIST_A(\d{4})\.ZIP", re.IGNORECASE)


def _years(values: Iterable[int]) -> list[int]:
    try:
        years = list(values)
    except TypeError as exc:
        raise ValueError("Expected years must be an iterable") from exc
    if not years or any(type(y) is not int or not 1986 <= y <= 2025 for y in years):
        raise ValueError("Allowed annual years are between 1986 and 2025; 2026 is a lockbox")
    if len(set(years)) != len(years):
        raise ValueError("Duplicate expected years")
    return sorted(years)


def audit_manual_archives(
    paths: Iterable[Path],
    *,
    expected_years: Iterable[int],
    acquisition_note: str,
) -> dict:
    """Audit annual ZIP files without extracting or publishing any quotations.

    acquisition_note is an audit trail supplied by the user, NOT verified legal
    authorization for redistribution, automation, or financial production.
    Missing expected years are reported explicitly; input ZIPs are never copied.
    """
    expected = _years(expected_years)
    if not isinstance(acquisition_note, str) or len(acquisition_note.strip()) < 8:
        raise ValueError("Document how annual files were obtained and licensing checked")
    try:
        archives = [Path(p) for p in paths]
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid archive paths") from exc
    if not archives:
        raise ValueError("Supply at least one annual ZIP file")
    found: dict[int, Path] = {}
    # Validate ALL filenames before touching any data: no accidental 2026 access.
    for path in archives:
        match = _NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Unexpected annual archive filename: {path.name}")
        year = int(match.group(1))
        if year >= 2026:
            raise PermissionError("The 2026 lockbox is excluded from all development checks")
        if year not in expected:
            raise ValueError(f"Unexpected year {year}; explicit expected_years is required")
        if year in found:
            raise ValueError(f"Duplicate annual archive for year {year}")
        if path.is_symlink():
            raise ValueError("Symbolic links are not accepted as source archives")
        found[year] = path

    reports = []
    totals = dict(lines_seen=0, quote_records_seen=0, valid_records=0,
                  duplicate_records=0, invalid_records=0, unsupported_market=0,
                  non_unit_quote_factor_records=0)
    for year, path in sorted(found.items()):
        quality = inspect_archive(path)
        counts = quality["counts"]
        quote_total = sum(counts.get(k, 0) for k in (
            "valid_records", "duplicate_records", "invalid_records",
            "unsupported_market"))
        if counts.get("quote_records_seen", 0) != quote_total:
            raise ValueError(f"Unreconciled quote records in {year}")
        first, last = quality["period_start"], quality["period_end"]
        if not first or not last or first[:4] != str(year) or last[:4] != str(year):
            raise ValueError(f"Accepted record dates do not match source year {year}")
        for key in totals:
            totals[key] += counts.get(key, 0)
        reports.append({
            "year": year, "source_filename": path.name,
            "source_sha256": quality["source_sha256"],
            "accepted_date_first": first, "accepted_date_last": last,
            "counts": {key: counts.get(key, 0) for key in totals},
            "fractional_zero_ohlc_with_trades": counts.get(
                "fractional_zero_ohlc_with_trades", 0),
            "quote_factor_counts": quality.get("quote_factor_counts", {}),
            "data_status": "DAILY_UNADJUSTED_NOT_ELIGIBLE_FOR_BACKTEST",
        })
    missing = sorted(set(expected) - set(found))
    return {
        "schema_version": 1,
        "status": "INCOMPLETE_FILES" if missing else "FILES_PRESENT_QA_ONLY",
        "expected_years": expected,
        "found_years": sorted(found),
        "missing_years": missing,
        "acquisition_note": acquisition_note.strip(),
        "acquisition_rights_independently_verified": False,
        "annual_reports": reports,
        "totals": totals,
        "history_type": "daily_unadjusted",
        "corporate_actions_validated": False,
        "point_in_time_universe_validated": False,
        "official_session_calendar_validated": False,
        "economic_backtest_authorized": False,
        "live_trading": "BLOCKED",
        "lockbox_2026_processed": False,
        "limitations": [
            "Manifest records self-reported acquisition; it does not confer data rights.",
            "Source completeness by trading session is NOT proven by annual ZIP presence.",
            "Factor-of-quotation is preserved but not interpreted as unit-price conversion.",
            "Prices have no validated dividends, splits, rights or point-in-time universe.",
            "Raw B3 archives and price series must not be committed to GitHub.",
        ],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Offline QA of manually obtained annual COTAHIST ZIPs")
    parser.add_argument("--years", required=True, help="Expected years, e.g. 2023,2024,2025")
    parser.add_argument("--acquisition-note", required=True,
                        help="Provenance/rights research note (not a legal authorization)")
    parser.add_argument("--report", type=Path,
                        help="Optional local JSON manifest, must not exist already")
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        expected = [int(y.strip()) for y in args.years.split(",")]
    except ValueError as exc:
        parser.error("Invalid comma-separated year list")
        raise AssertionError from exc
    if args.report is not None and args.report.exists():
        raise FileExistsError("Refusing to overwrite prior audit manifest")
    result = audit_manual_archives(
        args.archives, expected_years=expected,
        acquisition_note=args.acquisition_note)
    body = json.dumps(result, indent=2, ensure_ascii=False)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(body + "\n", encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
