import csv
import html
import json
from pathlib import Path

from .trade_analytics import reconstruct_closed_episodes
from .risk_metrics import expectancy_from_closed_trades, maximum_drawdown

def write_report(folder: Path, result: dict, manifest: dict, parameters: dict):
    folder.mkdir(parents=True, exist_ok=False)
    synthetic = manifest["provenance"]["synthetic"]
    episodes = reconstruct_closed_episodes(result["fills"])
    equity_marks = [parameters["policy"]["capital"]] + [row["equity"] for row in result["curve"]]
    drawdown = maximum_drawdown(equity_marks)
    expectancy = expectancy_from_closed_trades([
        item["pnl_after_estimated_costs_before_tax_brl"]
        for item in episodes["closed_episodes"]
    ])
    risk_diagnostics = {
        "status": "DESCRIPTIVE_PRETAX_SIMULATION_ONLY_NO_ALPHA_CLAIM",
        "open_positions_excluded": episodes["open_episode_count"],
        "closed_episodes": episodes["closed_episode_count"],
        "closed_pnl_after_estimated_costs_before_tax_brl": episodes["closed_pnl_pretax_brl"],
        "expectancy_after_estimated_costs_before_tax_brl": expectancy["expectancy_brl"],
        "expectancy_analysis": expectancy,
        "drawdown_analysis": drawdown,
        "trading_costs_confirmed": parameters.get("costs", {}).get("confirmed", False),
        "taxes_accounted": False,
        "scientific_validation": "NOT_EVALUATED",
        "limitations": episodes["warnings"] + [
            "Trade expectancy excludes open positions, taxation and uncertain real execution costs.",
            "Drawdown includes marked open inventory and may exceed stop or daily-loss plans.",
        ],
    }
    summary = {k:v for k,v in result.items() if k not in {"curve", "fills", "decisions"}}
    summary.update({"synthetic": synthetic, "scientific_decision": "INCONCLUSIVE", "g0": "REQUIRES_DATA",
                    "g2": "NOT_EVALUATED", "g3": "NOT_EVALUATED", "g6": "BLOCKED",
                    "parameters": parameters, "dataset_hash": manifest["data_sha256"],
                    "risk_diagnostics": risk_diagnostics,
                    "interpretation": "Teste funcional sintético; sem evidência de alfa." if synthetic else "Exploração com modelo de execução aproximado; sem decisão científica final."})
    (folder/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    for name in ("curve", "fills", "decisions"):
        rows = result[name]
        with (folder/f"{name}.csv").open("w", newline="", encoding="utf-8") as fp:
            cols = list(rows[0]) if rows else ["status"]
            writer = csv.DictWriter(fp, fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)
    with (folder/"closed_episodes.csv").open("w", newline="", encoding="utf-8") as fp:
        cols = ("symbol", "first_buy_timestamp", "last_sell_timestamp",
                "bought_qty", "sold_qty", "entry_orders", "exit_orders",
                "buy_notional_brl", "sell_notional_brl", "fees_brl",
                "pnl_after_estimated_costs_before_tax_brl")
        writer = csv.DictWriter(fp, fieldnames=cols)
        writer.writeheader()
        writer.writerows(episodes["closed_episodes"])
    with (folder/"open_episodes.csv").open("w", newline="", encoding="utf-8") as fp:
        cols = ("symbol", "first_buy_timestamp", "remaining_qty",
                "entry_orders", "partial_exit_orders", "status")
        writer = csv.DictWriter(fp, fieldnames=cols)
        writer.writeheader()
        writer.writerows(episodes["open_episodes"])
    curve = result["curve"]
    equities = equity_marks
    low, high = min(equities), max(equities)
    span = high-low or 1
    points = " ".join(f"{30+i*840/max(1,len(equities)-1):.2f},{210-(v-low)*170/span:.2f}" for i,v in enumerate(equities))
    label = "DADOS SINTÉTICOS — TESTE DE CÓDIGO" if synthetic else "EXPLORAÇÃO — EXECUÇÃO APROXIMADA"
    esc = html.escape
    expectation_label = ("Não calculada: sem operações encerradas"
                         if expectancy["expectancy_brl"] is None
                         else f"R$ {expectancy['expectancy_brl']:.2f} por episódio")
    risk_table = (
        "<section><h2>Expectância e sobrevivência — somente simulação</h2>"
        "<p>Resultado após custos estimados e <strong>antes de impostos</strong>. "
        "Expectância observada não é previsão de lucro nem evidência de alfa.</p>"
        "<table><tr><th>Medida</th><th>Valor</th></tr>"
        f"<tr><td>Episódios completamente encerrados</td><td>{episodes['closed_episode_count']}</td></tr>"
        f"<tr><td>Episódios ainda abertos (excluídos da expectância)</td>"
        f"<td>{episodes['open_episode_count']}</td></tr>"
        f"<tr><td>Expectância descritiva antes de impostos</td><td>{esc(expectation_label)}</td></tr>"
        f"<tr><td>Drawdown máximo patrimonial</td><td>R$ {drawdown['max_drawdown_brl']:.2f} "
        f"({drawdown['max_drawdown_fraction']*100:.2f}%)</td></tr>"
        "<tr><td>Conclusão científica</td><td>INCONCLUSIVO — custos e execução não validados</td></tr>"
        "</table></section>"
    )
    body = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nazaret Quant Relatório de pesquisa</title><style>body{{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:0 24px;color:#182333;background:#f5f7fa}}h1{{margin-bottom:0}}small{{color:#45556b}}.status{{background:#ffedbf;padding:16px;font-weight:700}}section{{background:white;padding:24px;margin:24px 0;border:1px solid #dce1e8;border-radius:8px}}svg{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;border:1px solid #dce1e8;padding:8px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Nazaret Quant</h1><small>Núcleo de pesquisa 0.1.0</small><p class="status">{label}</p>
<section><h2>Resultado desta execução</h2><p>{esc(summary['interpretation'])}</p>
<table><tr><th>Medida</th><th>Valor</th></tr><tr><td>Variação patrimonial simulada antes de tributos</td><td>R$ {result['pnl_before_tax']:.2f}</td></tr>
<tr><td>Caixa final</td><td>R$ {result['final_cash']:.2f}</td></tr><tr><td>Patrimônio marcado</td><td>R$ {result['final_equity']:.2f}</td></tr>
<tr><td>Execuções simuladas</td><td>{len(result['fills'])}</td></tr><tr><td>Decisão científica</td><td>INCONCLUSIVO</td></tr><tr><td>Ordens reais</td><td>BLOQUEADAS</td></tr></table></section>
{risk_table}
<section><h2>Patrimônio na simulação</h2><p>Marcação inclui posições abertas. Escala vertical de R$ {low:.2f} a R$ {high:.2f}.</p>
<svg viewBox="0 0 900 240" role="img" aria-label="Curva patrimonial simulada"><path d="M30 20 V210 H880" fill="none" stroke="#b8c4d2"/><polyline points="{points}" fill="none" stroke="#1e5776" stroke-width="3"/></svg></section>
<section><h2>Limitações e alertas</h2><ul>{''.join('<li>'+esc(x)+'</li>' for x in result['limitations'])}</ul><pre>{esc(json.dumps(result['alerts'],indent=2,ensure_ascii=False))}</pre></section>
<section><h2>Rastreabilidade</h2><p>Hash dos dados: {esc(manifest['data_sha256'])}</p><pre>{esc(json.dumps(parameters,indent=2,ensure_ascii=False))}</pre></section></html>'''
    (folder/"report.html").write_text(body, encoding="utf-8")
    return summary
