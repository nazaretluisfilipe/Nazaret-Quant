from pathlib import Path
from zipfile import ZipFile
pytest = __import__('pytest')
from nazaret_quant.b3_cotahist import parse_quote, inspect_archive

def test_parse_quote_short_record():
    with pytest.raises(ValueError, match="menor que 245"):
        parse_quote(b"01SHORT")

def test_inspect_archive_missing_txt(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(p, "w") as z:
        z.writestr("OTHER.DAT", b"NOT A COTAHIST TXT")
    with pytest.raises(ValueError, match="exatamente um TXT"):
        inspect_archive(p)
