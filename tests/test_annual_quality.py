"""Synthetic-only tests: no historical B3 ZIPs or lockbox content."""
from pathlib import Path
from zipfile import ZipFile

import pytest

from nazaret_quant.annual_quality import audit_manual_archives, main


def fake_record(date="20251021", market="010", quote_factor=1):
    record = [" "] * 245

    def put(i, j, val):
        record[i:j] = list(str(val).ljust(j-i)[:j-i])

    def numeric(i, j, val):
        record[i:j] = list(str(val).zfill(j-i))

    put(0, 2, "01")
    put(2, 10, date)
    put(12, 24, "ABCD3F" if market == "020" else "ABCD3")
    put(24, 27, market)
    for a, b, val in [
        (56, 69, 1100), (69, 82, 1200), (82, 95, 900),
        (95, 108, 1010), (108, 121, 1110),
        (147, 152, 5), (152, 170, 100),
        (170, 188, 110000), (210, 217, quote_factor),
    ]:
        numeric(a, b, val)
    put(230, 242, "BRSYNTH00000")
    return "".join(record).encode("latin-1")


def archive(folder: Path, year: int, *, invalid: bool = False,
            quote_factor: int = 1) -> Path:
    path = folder / f"COTAHIST_A{year}.ZIP"
    sample = fake_record(date=f"{year}1021", quote_factor=quote_factor)
    with ZipFile(path, "w") as zip_file:
        zip_file.writestr(
            f"COTAHIST_A{year}.TXT",
            b"00HEADER\n" + sample + b"\n"
            + (b"01SHORT\n" if invalid else b"")
            + b"99FOOTER\n",
        )
    return path


def test_batch_reconciles_counts_hashes_and_factor(tmp_path):
    p = archive(tmp_path, 2024, quote_factor=100)
    q = archive(tmp_path, 2025, invalid=True)
    result = audit_manual_archives([q, p], expected_years=[2025, 2024],
                                   acquisition_note="Local synthetic fixtures only")
    assert result["status"] == "FILES_PRESENT_QA_ONLY"
    assert result["missing_years"] == []
    assert result["found_years"] == [2024, 2025]
    assert result["totals"]["valid_records"] == 2
    assert result["totals"]["invalid_records"] == 1
    assert result["totals"]["quote_records_seen"] == 3
    assert result["totals"]["non_unit_quote_factor_records"] == 1
    assert result["annual_reports"][0]["quote_factor_counts"] == {100: 1}
    assert len(result["annual_reports"][0]["source_sha256"]) == 64
    assert result["economic_backtest_authorized"] is False
    assert result["lockbox_2026_processed"] is False
    assert "open" not in result["annual_reports"][0]  # No raw OHLC output


def test_missing_year_visible_not_falsely_cleared(tmp_path):
    p = archive(tmp_path, 2025)
    r = audit_manual_archives([p], expected_years=[2023, 2024, 2025],
                              acquisition_note="Local synthetic fixtures only")
    assert r["status"] == "INCOMPLETE_FILES"
    assert r["missing_years"] == [2023, 2024]


def test_2026_blocked_even_before_reading_data(tmp_path, monkeypatch):
    p = tmp_path / "COTAHIST_A2026.ZIP"
    p.write_bytes(b"should never inspect this content")
    def forbidden(*args, **kwargs):
        raise AssertionError("Should never inspect the 2026 archive")
    monkeypatch.setattr("nazaret_quant.annual_quality.inspect_archive", forbidden)
    with pytest.raises(PermissionError, match="2026"):
        audit_manual_archives([p], expected_years=[2025],
                              acquisition_note="Local synthetic fixtures only")


def test_no_partial_scan_if_any_input_is_2026(tmp_path, monkeypatch):
    p = archive(tmp_path, 2025)
    q = tmp_path / "COTAHIST_A2026.ZIP"
    q.write_bytes(b"lockbox")
    monkeypatch.setattr("nazaret_quant.annual_quality.inspect_archive",
                        lambda *_: (_ for _ in ()).throw(AssertionError("would read")))
    with pytest.raises(PermissionError):
        audit_manual_archives([p, q], expected_years=[2025],
                              acquisition_note="Local synthetic fixtures only")


@pytest.mark.parametrize("years,filenames", [
    ([2025], ["COTAHIST_A2024.ZIP"]),
    ([2025], ["COTAHIST_A2025.ZIP", "COTAHIST_A2025.zip"]),
    ([2026], ["COTAHIST_A2025.ZIP"]),
    ([2025, 2025], ["COTAHIST_A2025.ZIP"]),
    ([2025], ["untrusted.zip"]),
])
def test_invalid_file_and_year_groups_fail(tmp_path, years, filenames):
    paths = [tmp_path / n for n in filenames]
    with pytest.raises((ValueError, PermissionError)):
        audit_manual_archives(paths, expected_years=years,
                              acquisition_note="Local synthetic fixtures only")


def test_source_year_mismatch_rejected(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(p, "w") as z:
        z.writestr("COTAHIST_A2025.TXT", fake_record("20241021") + b"\n")
    with pytest.raises(ValueError, match="source year"):
        audit_manual_archives([p], expected_years=[2025],
                              acquisition_note="Local synthetic fixtures only")


def test_cli_creates_manifest_once_and_does_not_overwrite(tmp_path, capsys):
    p = archive(tmp_path, 2025)
    out = tmp_path / "audit.json"
    args = ["--years", "2025", "--acquisition-note",
            "Local synthetic fixtures only", "--report", str(out), str(p)]
    main(args)
    assert out.exists()
    assert '"status": "FILES_PRESENT_QA_ONLY"' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        main(args)
