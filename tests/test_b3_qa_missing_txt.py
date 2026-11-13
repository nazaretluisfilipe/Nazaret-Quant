from pathlib import Path
from zipfile import ZipFile
import pytest
from nazaret_quant.b3_cotahist import inspect_archive

def test_inspect_archive_missing_txt(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(p, "w") as z:
        z.writestr("OTHER.DAT", b"some data\n")
    with pytest.raises(ValueError, match="ZIP deve conter exatamente um TXT COTAHIST"):
        inspect_archive(p)
