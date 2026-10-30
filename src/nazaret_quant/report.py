import csv
import html
import json
from pathlib import Path

def write_report(folder: Path, result: dict, manifest: dict, parameters: dict):
    folder.mkdir(parents=True, exist_ok=False)
    synthetic = manifest["provenance"]["synthetic"]
    summary = {k:v for k,v in result.items() if k not in {"curve", "fills", "decisions"}}
    summary.update({"synthetic": synthetic, "scientific_decision": "INCONCLUSIVE", "g0": "REQUIRES_DATA",
                    "g2": "NOT_EVALUATED", "g3": "NOT_EVALUATED", "g6": "BLOCKED",
                    "parameters": parameters, "dataset_hash": manifest["data_sha256"],
                    "interpretation": "Teste funcional sintético; sem evidência de alfa." if synthetic else "Exploração com modelo de execução aproximado; sem decisão científica final."})
    (folder/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    for name in ("curve", "fills", "decisions"):
        rows = result[name]
        with (folder/f"{name}.csv").open("w", newline="", encoding="utf-8") as fp:
            cols = list(rows[0]) if rows else ["status"]
            writer = csv.DictWriter(fp, fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)
    curve = result["curve"]
    equities = [parameters["policy"]["capital"]] + [x["equity"] for x in curve]
    low, high = min(equities), max(equities)
    span = high-low or 1
    points = " ".join(f"{30+i*840/max(1,len(equities)-1):.2f},{210-(v-low)*170/span:.2f}" for i,v in enumerate(equities))
    label = "DADOS SINTÉTICOS — TESTE DE CÓDIGO" if synthetic else "EXPLORAÇÃO — EXECUÇÃO APROXIMADA"
    esc = html.escape
    body = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nazaret Quant Relatório de pesquisa</title><style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#182333;background:#f5f7fa}}h1{{margin-bottom:0}}small{{color:#45556b}}.status{{background:#ffedbf;padding:16px;font-weight:700}}section{{background:white;padding:24px;margin:24px 0;border:1px solid #dce1e8;border-radius:8px}}svg{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;border:1px solid #dce1e8;padding:8px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Nazaret Quant</h1><small>Núcleo de pesquisa 0.1.0</small><p class="status">{label}</p>
<section><h2>Resultado desta execução</h2><p>{esc(summary['interpretation'])}</p>
<table><tr><th>Medida</th><th>Valor</th></tr><tr><td>Variação patrimonial simulada antes de tributos</td><td>R$ {result['pnl_before_tax']:.2f}</td></tr>
<tr><td>Caixa final</td><td>R$ {result['final_cash']:.2f}</td></tr><tr><td>Patrimônio marcado</td><td>R$ {result['final_equity']:.2f}</td></tr>
<tr><td>Execuções simuladas</td><td>{len(result['fills'])}</td></tr><tr><td>Decisão científica</td><td>INCONCLUSIVO</td></tr><tr><td>Ordens reais</td><td>BLOQUEADAS</td></tr></table></section>
<section><h2>Patrimônio na simulação</h2><p>Marcação inclui posições abertas. Escala vertical de R$ {low:.2f} a R$ {high:.2f}.</p>
<svg viewBox="0 0 900 240" role="img" aria-label="Curva patrimonial simulada"><path d="M30 20 V210 H880" fill="none" stroke="#b8c4d2"/><polyline points="{points}" fill="none" stroke="#1e5776" stroke-width="3"/></svg></section>
<section><h2>Limitações e alertas</h2><ul>{''.join('<li>'+esc(x)+'</li>' for x in result['limitations'])}</ul><pre>{esc(json.dumps(result['alerts'],indent=2,ensure_ascii=False))}</pre></section>
<section><h2>Rastreabilidade</h2><p>Hash dos dados: {esc(manifest['data_sha256'])}</p><pre>{esc(json.dumps(parameters,indent=2,ensure_ascii=False))}</pre></section></html>'''
    (folder/"report.html").write_text(body, encoding="utf-8")
    return summary
