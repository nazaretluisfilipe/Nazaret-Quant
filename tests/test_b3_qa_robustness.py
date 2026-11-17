from pathlib import Path
from zipfile import ZipFile
import pytest
from nazaret_quant.b3_cotahist import inspect_archive
from tests.test_b3_cotahist import example

def test_inspect_archive_max_records_and_missing_txt(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    content = b"00HEADER\n" + example(symbol="VALE3") + b"\n" + example(symbol="ITUB4") + b"\n99FOOTER\n"
    with ZipFile(p, "w") as z:
        z.writestr("COTAHIST_A2025.TXT", content)
    
    # Teste max_records
    res = inspect_archive(p, max_records=1)
    assert res["counts"]["valid_records"] == 1
    assert res["counts"].get("sample_only") == 1

    # Teste arquivo sem TXT
    bad_zip = tmp_path / "BAD.ZIP"
    with ZipFile(bad_zip, "w") as z:
        z.writestr("OTHER.DAT", b"DATA")
    with pytest.raises(ValueError, match="ZIP deve conter exatamente um TXT COTAHIST"):
        inspect_archive(bad_zip)

    # Teste arquivo inválido (não zip)
    not_zip = tmp_path / "NOTAZIP.ZIP"
    not_zip.write_text("not a zip")
    with pytest.raises(Exception):
        inspect_archive(not_zip)
