from pathlib import Path
from zipfile import ZipFile
import pytest
from nazaret_quant.b3_cotahist import inspect_archive

def test_inspect_archive_validation_edge_cases(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    # Verifica rejeição limpa de múltiplos arquivos TXT, arquivos não ZIP e contagens de rejeição
    with ZipFile(p, "w") as z:
        z.writestr("A.TXT", b"00HEADER\n")
        z.writestr("B.TXT", b"00HEADER\n")
    with pytest.raises(ValueError, match="exatamente um TXT"):
        inspect_archive(p)

    p_not_zip = tmp_path / "not_a_zip.txt"
    p_not_zip.write_text("dados")
    with pytest.raises(ValueError, match="Forneça arquivo ZIP"):
        inspect_archive(p_not_zip)

    # Arquivo com max_records restrito
    p_valid = tmp_path / "COTAHIST_A2025.ZIP"
    with ZipFile(p_valid, "w") as z:
        z.writestr("COTAHIST.TXT", b"00HEAD\n01" + b" " * 240 + b"\n99FOOT\n")
    with pytest.raises(ValueError):
        inspect_archive(p_valid, max_records=0)
