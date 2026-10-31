"""Testes do importador diário B3 com registros artificiais de largura fixa."""
from pathlib import Path
from zipfile import ZipFile
import pytest
from nazaret_quant.b3_cotahist import parse_quote, inspect_archive

def example(market="010", symbol="ABCD3", date="20251021", open_=1000, high=1100, low=900, close=1050, factor=1):
    f=[" "]*245
    def put(a,b,t): f[a:b]=list(str(t).ljust(b-a)[:b-a])
    def num(a,b,n): f[a:b]=list(str(n).zfill(b-a))
    put(0,2,"01");put(2,10,date);put(24,27,market);put(12,24,symbol)
    for a,b,v in [(56,69,open_),(69,82,high),(82,95,low),(95,108,1020),(108,121,close),
                  (147,152,100),(152,170,5000),(170,188,5000000)]:num(a,b,v)
    num(210,217,factor)
    put(230,242,"BRTEST000000")
    return "".join(f).encode("latin-1")

def test_parse_quote():
    r=parse_quote(example())
    assert r["date"]=="2025-10-21" and r["symbol"]=="ABCD3"
    assert r["close"]==10.50 and r["market"]=="spot_lot"
    assert r["quantity"]==5000 and r["financial_volume"]==50000.0
    assert parse_quote(example(market="050")) is None
    assert parse_quote(example(market="020"))["market"]=="spot_fractional"

@pytest.mark.parametrize("raw",[b"01abc",example(high=950),example(date="20250230")])
def test_invalid_record(raw):
    with pytest.raises(ValueError):parse_quote(raw)

def test_inspect_zip_and_lockbox(tmp_path):
    p=tmp_path/"COTAHIST_A2025.ZIP"
    with ZipFile(p,"w") as z:
        z.writestr("COTAHIST_A2025.TXT",b"00HEADER\n"+example()+b"\r\n"+example()+b"\r\n"+example(market="020")+b"\n99FOOTER\n")
    out=tmp_path/"summary.csv"
    q=inspect_archive(p,output=out)
    assert q["counts"]["valid_records"]==2
    assert q["counts"]["duplicate_records"]==1
    assert q["period_start"]=="2025-10-21"
    assert len(out.read_text().splitlines())==3
    with pytest.raises(FileExistsError):inspect_archive(p,output=out)
    lock=tmp_path/"COTAHIST_A2026.ZIP"
    p.rename(lock)
    with pytest.raises(PermissionError): inspect_archive(lock)

def test_quote_factor_is_explicit_and_ohlc_not_silently_rescaled():
    usual = parse_quote(example())
    alternate = parse_quote(example(factor=1000))
    assert usual["quote_factor"] == 1
    assert alternate["quote_factor"] == 1000
    assert alternate["close"] == usual["close"]  # quoted value, NOT unit price
    with pytest.raises(ValueError, match="Fator"):
        parse_quote(example(factor=0))


def test_fractional_zero_ohlc_with_trades_is_classified_not_imputed(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    # This fixture reproduces the observed 2025 anomaly, without raw market data.
    anomaly = example(market="020", open_=0, high=0, low=0, close=0, factor=1000)
    with ZipFile(p, "w") as z:
        z.writestr("COTAHIST_A2025.TXT", b"00HEADER\n" + anomaly + b"\n"
                   + example(factor=100) + b"\n99FOOTER\n")
    q = inspect_archive(p)
    assert q["counts"]["invalid_records"] == 1
    assert q["counts"]["fractional_zero_ohlc_with_trades"] == 1
    assert q["counts"]["valid_records"] == 1
    assert q["counts"]["non_unit_quote_factor_records"] == 1
    assert q["quote_factor_counts"] == {100: 1}
    assert q["invalid_samples"][0]["category"] == "fractional_zero_ohlc_with_trades"

def test_inspect_archive_malformed_and_edge_cases(tmp_path):
    p = tmp_path / "COTAHIST_A2025.ZIP"
    # Inclui linha curta, linha com data inválida e linhas duplicadas com variações
    content = (
        b"00HEADER\n"
        b"01SHORTLINE\n"
        + example(date="20251301") + b"\n"
        + example(symbol="PETR4", date="20250102") + b"\n"
        + example(symbol="PETR4", date="20250102") + b"\n"
        + b"99FOOTER\n"
    )
    with ZipFile(p, "w") as z:
        z.writestr("COTAHIST_A2025.TXT", content)
    res = inspect_archive(p)
    assert res["counts"]["invalid_records"] >= 2
    assert res["counts"]["valid_records"] == 1
    assert res["counts"]["duplicate_records"] == 1
