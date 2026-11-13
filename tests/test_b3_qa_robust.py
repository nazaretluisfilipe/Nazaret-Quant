from pathlib import Path
from zipfile import ZipFile
import pytest
from nazaret_quant.b3_cotahist import inspect_archive

def test_inspect_archive_missing_or_multiple_txt(tmp_path):
    p_empty = tmp_path / "EMPTY.ZIP"
    with ZipFile(p_empty, "w") as z:
        pass
    with pytest.raises(ValueError, match="ZIP deve conter exatamente um TXT COTAHIST"):
        inspect_archive(p_empty)

    p_multi = tmp_path / "MULTI.ZIP"
    with ZipFile(p_multi, "w") as z:
        z.writestr("file1.txt", b"content")
        z.writestr("file2.txt", b"content")
    with pytest.raises(ValueError, match="ZIP deve conter exatamente um TXT COTAHIST"):
        inspect_archive(p_multi)

def test_inspect_archive_invalid_max_records(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(p, "w") as z:
        z.writestr("COTAHIST_A2025.TXT", b"00HEADER\n99FOOTER\n")
    with pytest.raises(ValueError, match="max_records precisa ser positivo"):
        inspect_archive(p, max_records=0)
