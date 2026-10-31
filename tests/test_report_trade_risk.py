"""End-to-end report diagnostics with only fictional ledger events."""
import csv
import json

import pytest

from nazaret_quant.ledger import Ledger
from nazaret_quant.report import write_report
from nazaret_quant.risk_metrics import expectancy_from_closed_trades, maximum_drawdown


def report(tmp_path, events, equities):
    result = {
        "fills": events, "curve": [
            {"timestamp": f"synthetic-{i}", "session": "synthetic",
             "cash": 250, "equity": e, "exposure": 0,
             "daily_halt": False, "permanent_halt": False}
            for i, e in enumerate(equities)
        ],
        "decisions": [], "alerts": [], "limitations": ["Artificial data only"],
        "final_cash": 250.0, "final_equity": equities[-1] if equities else 250.0,
        "pnl_before_tax": (equities[-1] if equities else 250.0)-250.0,
        "positions": {}, "live_trading": "BLOCKED",
    }
    manifest = {"provenance": {"synthetic": True}, "data_sha256": "only-fiction"}
    parameters = {"policy": {"capital": 250}, "costs": {"confirmed": False}}
    target = tmp_path / "analysis"
    summary = write_report(target, result, manifest, parameters)
    return summary, target


def test_report_only_closed_trades_enter_expectancy(tmp_path):
    ledger = Ledger()
    ledger.execute("1", "t0", "AAA3", "BUY", 5, 10, 0.5)
    ledger.execute("2", "t1", "AAA3", "SELL", 5, 9, 0.5)
    ledger.execute("3", "t2", "BBB4", "BUY", 2, 10, 0)
    summary, target = report(tmp_path, ledger.events, [249, 244, 239, 242])
    risk = summary["risk_diagnostics"]
    assert risk["closed_episodes"] == 1
    assert risk["open_positions_excluded"] == 1
    assert risk["closed_pnl_after_estimated_costs_before_tax_brl"] == -6
    assert risk["expectancy_after_estimated_costs_before_tax_brl"] == -6
    assert risk["drawdown_analysis"]["max_drawdown_brl"] == 11
    assert risk["taxes_accounted"] is False
    assert risk["trading_costs_confirmed"] is False
    assert risk["scientific_validation"] == "NOT_EVALUATED"
    assert (target/"closed_episodes.csv").exists()
    with (target/"closed_episodes.csv").open(newline="", encoding="utf-8") as fp:
        closed = list(csv.DictReader(fp))
    assert len(closed) == 1 and closed[0]["symbol"] == "AAA3"
    assert closed[0]["pnl_after_estimated_costs_before_tax_brl"] == "-6.0"
    with (target/"open_episodes.csv").open(newline="", encoding="utf-8") as fp:
        opened = list(csv.DictReader(fp))
    assert len(opened) == 1 and opened[0]["symbol"] == "BBB4"
    html = (target/"report.html").read_text(encoding="utf-8")
    assert "Expectância e sobrevivência" in html
    assert "antes de impostos" in html
    assert "DADOS SINTÉTICOS" in html
    assert json.loads((target/"summary.json").read_text())["scientific_decision"] == "INCONCLUSIVE"


def test_empty_operations_do_not_fabricate_expectancy_or_drawdown(tmp_path):
    summary, target = report(tmp_path, [], [])
    risk = summary["risk_diagnostics"]
    assert risk["expectancy_after_estimated_costs_before_tax_brl"] is None
    assert risk["closed_episodes"] == 0
    assert risk["drawdown_analysis"]["max_drawdown_fraction"] == 0
    assert "Não calculada" in (target/"report.html").read_text()
    assert len((target/"closed_episodes.csv").read_text().splitlines()) == 1


def test_partial_exit_not_counted_as_closed(tmp_path):
    ledger = Ledger()
    ledger.execute("1", "t", "AAA3", "BUY", 10, 10, 0)
    ledger.execute("2", "t", "AAA3", "SELL", 3, 11, 0)
    summary, target = report(tmp_path, ledger.events, [250, 255])
    assert summary["risk_diagnostics"]["closed_episodes"] == 0
    assert summary["risk_diagnostics"]["open_positions_excluded"] == 1
    assert summary["risk_diagnostics"]["expectancy_after_estimated_costs_before_tax_brl"] is None
    assert len((target/"open_episodes.csv").read_text().splitlines()) == 2


def test_three_consecutive_losses_do_not_become_profitable_by_aggregation(tmp_path):
    ledger = Ledger()
    for i in range(3):
        ledger.execute(f"B{i}", f"t{i}", "AAA3", "BUY", 2, 10, 0)
        ledger.execute(f"S{i}", f"t{i}", "AAA3", "SELL", 2, 9, 0)
    summary, _ = report(tmp_path, ledger.events, [248, 246, 244])
    risk = summary["risk_diagnostics"]
    assert risk["closed_episodes"] == 3
    assert risk["expectancy_after_estimated_costs_before_tax_brl"] == -2
    assert risk["expectancy_analysis"]["win_rate"] == 0
    assert risk["drawdown_analysis"]["max_drawdown_brl"] == 6
    assert risk["scientific_validation"] == "NOT_EVALUATED"
