"""Leitor offline e conservador do layout COTAHIST (registros fixos).

Não substitui dados ajustados de eventos corporativos, calendários ou cotações intradiárias.
Não aciona ordens nem abre lockbox. Arquivos da B3 não são redistribuídos.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

MARKETS = {"010": "spot_lot", "020": "spot_fractional"}
FIELDS = ("date", "symbol", "market", "open", "high", "low", "average", "close",
          "trades", "quantity", "financial_volume", "isin", "quote_factor")

def _integer(record: str, start: int, end: int) -> int:
    value = record[start:end]
    if not value.strip().isdigit():
        raise ValueError(f"Campo numérico inválido [{start}:{end}]")
    return int(value)

def parse_quote(raw: bytes) -> dict | None:
    """Converte um registro 01 do layout público de largura fixa, preços /100."""
    if len(raw) < 245:
        raise ValueError("Registro COTAHIST menor que 245 caracteres")
    r = raw.decode("latin-1")
    if r[:2] != "01":
        return None
    market = r[24:27]
    if market not in MARKETS:
        return None
    date = r[2:10]
    if len(date) != 8 or not date.isdigit():
        raise ValueError("Data inválida")
    # ISO validation catches 20250230, etc.
    from datetime import date as d
    d(int(date[:4]), int(date[4:6]), int(date[6:]))
    symbol = r[12:24].strip()
    if not symbol:
        raise ValueError("Símbolo vazio")
    prices = {name: _integer(r, a, b) / 100 for name, a, b in (
        ("open",56,69), ("high",69,82), ("low",82,95),
        ("average",95,108), ("close",108,121))}
    if min(prices.values()) <= 0 or prices["low"] > min(prices["open"],prices["close"]) or prices["high"] < max(prices["open"],prices["close"]) or prices["high"] < prices["low"]:
        raise ValueError("OHLC inconsistente")
    quote_factor = _integer(r,210,217)
    if quote_factor <= 0:
        raise ValueError("Fator de cotação inválido")
    trades = _integer(r,147,152)
    quantity = _integer(r,152,170)
    turnover = _integer(r,170,188) / 100
    return {"date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "symbol": symbol,
            "market": MARKETS[market], **prices, "trades": trades,
            "quantity": quantity, "financial_volume": turnover,
            "isin": r[230:242].strip(), "quote_factor": quote_factor}

def source_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def _rejection_category(raw: bytes, error: Exception) -> str:
    """Categoriza anomalia sem deduzir preços ausentes ou corrigir dados."""
    if str(error) != "OHLC inconsistente" or len(raw) < 245 or raw[24:27] != b"020":
        return "other_invalid"
    try:
        ohlc = (raw[56:69], raw[69:82], raw[82:95], raw[108:121])
        if (all(field.isdigit() and int(field) == 0 for field in ohlc)
            and int(raw[95:108]) > 0
            and int(raw[147:152]) > 0
            and int(raw[152:170]) > 0):
            return "fractional_zero_ohlc_with_trades"
    except ValueError:
        pass
    return "other_invalid"

def inspect_archive(path: Path, *, output: Path | None = None, max_records: int | None = None,
                    lockbox: bool = False) -> dict:
    """Inspeciona ZIP sem extraí-lo; CSV só quando explicitamente autorizado.

    Por padrão, 2026 é lockbox: cabeçalho e cotação não são lidos sem autorização.
    """
    if not path.is_file() or path.suffix.lower() != ".zip":
        raise ValueError("Forneça arquivo ZIP COTAHIST existente")
    name = path.name.upper()
    if "A2026" in name and not lockbox:
        raise PermissionError("Arquivo 2026 reservado como lockbox; inspeção bloqueada")
    if output is not None and output.exists():
        raise FileExistsError("Saída existente não pode ser sobrescrita")
    if max_records is not None and max_records <= 0:
        raise ValueError("max_records precisa ser positivo")
    counts = Counter()
    first = last = None
    seen = set()
    bad_examples = []
    quote_factors = Counter()
    writer = None
    fout = None
    try:
        with ZipFile(path) as z:
            names = [n for n in z.namelist() if n.upper().endswith(".TXT")]
            if len(names) != 1:
                raise ValueError("ZIP deve conter exatamente um TXT COTAHIST")
            if output:
                output.parent.mkdir(parents=True,exist_ok=True)
                fout = output.open("x",newline="",encoding="utf-8")
                writer = csv.DictWriter(fout,fieldnames=FIELDS)
                writer.writeheader()
            with z.open(names[0]) as f:
                for raw in f:
                    counts["lines_seen"] += 1
                    if raw.startswith((b"00",b"99")):
                        counts["non_quote_records"] += 1
                        continue
                    if not raw.startswith(b"01"):
                        counts["unknown_records"] += 1
                        continue
                    counts["quote_records_seen"] += 1
                    try:
                        record=parse_quote(raw.rstrip(b"\r\n"))
                    except (ValueError,UnicodeError) as exc:
                        counts["invalid_records"] += 1
                        category = _rejection_category(raw.rstrip(b"\r\n"), exc)
                        counts[category] += 1
                        if len(bad_examples)<10:
                            bad_examples.append({"line":counts["lines_seen"],"error":str(exc),
                                                 "category":category})
                        continue
                    if record is None:
                        counts["unsupported_market"] += 1
                        continue
                    key=record["date"]+"|"+record["symbol"]+"|"+record["market"]
                    if key in seen:
                        counts["duplicate_records"] += 1
                        continue
                    seen.add(key)
                    counts["valid_records"] += 1
                    quote_factors[record["quote_factor"]] += 1
                    if record["quote_factor"] != 1:
                        counts["non_unit_quote_factor_records"] += 1
                    first=min(first,record["date"]) if first else record["date"]
                    last=max(last,record["date"]) if last else record["date"]
                    counts[record["market"]] += 1
                    if writer:
                        writer.writerow(record)
                    if max_records is not None and counts["quote_records_seen"] >= max_records:
                        counts["sample_only"] = 1
                        break
    finally:
        if fout:
            fout.close()
    quality={"input":path.name,"source_sha256":source_hash(path),
             "period_start":first,"period_end":last,"counts":dict(counts),
             "invalid_samples":bad_examples,"quote_factor_counts":dict(sorted(quote_factors.items())),
             "date_type":"daily_unadjusted",
             "research_status":"ENGINEERING_QA_ONLY_NO_ALPHA_CLAIM",
             "limitations":["Sem ajustes corporativos; não usar para P&L antes de validar proventos/desdobramentos",
                            "Sem candles intradiários nem spread executável",
                            "Fatores de cotação não unitários permanecem como metadados; não há preço unitário convertido",
                            "Amostra parcial não habilita pesquisa econômica",
                            "Autorização/licença e uso de dados devem ser verificados"],
             "live_trading":"BLOCKED"}
    return quality

def main(argv=None):
    ap=argparse.ArgumentParser(description="Inspeção offline COTAHIST, sem negociações reais")
    ap.add_argument("zip_file",type=Path)
    ap.add_argument("--output-csv",type=Path)
    ap.add_argument("--max-records",type=int)
    ap.add_argument("--allow-2026-lockbox",action="store_true")
    args=ap.parse_args(argv)
    print(json.dumps(inspect_archive(args.zip_file,output=args.output_csv,max_records=args.max_records,
                                     lockbox=args.allow_2026_lockbox),ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
