from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
import yaml
from .data import ingest, load_snapshot, sha256
from .engine import Policy, run
from .ledger import Costs
from .registry import Registry
from .report import write_report
from .research import cost_map, mde
from .strategies import Baseline

def code_revision():
    root = Path(__file__).resolve().parents[2]
    import hashlib
    digest = hashlib.sha256()
    paths = list((root/"src").rglob("*.py")) + list((root/"config").glob("*.yaml")) + [root/"pyproject.toml"]
    for p in sorted(paths):
        digest.update(str(p.relative_to(root)).encode())
        digest.update(p.read_bytes())
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    return {"commit": commit, "source_sha256": digest.hexdigest()}

def generate_demo(folder):
    folder.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261030)
    rows, price = [], 10.0
    for date in ("2026-01-05", "2026-01-06", "2026-01-07"):
        for i in range(84):
            opening = pd.Timestamp(date + " 10:00", tz="America/Sao_Paulo") + pd.Timedelta(minutes=5*i)
            op = price
            price = max(1, op * (1+rng.normal(0, .002)))
            rows.append({"bar_open": opening.isoformat(), "timestamp": (opening+pd.Timedelta(minutes=5)).isoformat(),
                         "session": date, "symbol": "SYNTH", "open": op, "high": max(op,price)*1.001,
                         "low": min(op,price)*.999, "close": price, "volume": 10000})
    pd.DataFrame(rows).to_csv(folder/"synthetic.csv", index=False)
    provenance = {"provider": "Nazaret synthetic generator", "license": "CC0 synthetic fixtures only",
        "license_evidence": "Generated locally without market data", "storage_authorized": True,
        "synthetic": True, "partition": "exploration"}
    ingest(folder/"synthetic.csv", folder/"snapshot", provenance)
    return folder/"snapshot"

def execute(snapshot, output, strategy, experiment, seed, scenario, config):
    if output.exists():
        raise FileExistsError("Saída existente; use outro experimento/diretório")
    settings = yaml.safe_load(config.read_text(encoding="utf-8"))
    costs, policy = Costs(**settings[scenario]), Policy()
    # Manifests e hashes são metadados; resultados só são lidos depois do registro.
    manifest = json.loads((snapshot/"manifest.json").read_text(encoding="utf-8"))
    if manifest["provenance"]["partition"] == "lockbox":
        raise PermissionError("Confirmação bloqueada neste MVP")
    output.parent.mkdir(parents=True, exist_ok=True)
    registry = Registry(output.parent/"experiments.sqlite")
    params = {"strategy": strategy, "seed": seed, "lookback": 3, "random_probability": .1,
              "costs": asdict(costs), "cost_scenario": scenario, "policy": asdict(policy),
              "code": code_revision(), "dataset_hash": manifest["data_sha256"],
              "manifest_sha256": sha256(snapshot/"manifest.json"),
              "partition": manifest["provenance"]["partition"], "hypothesis": "ENGINEERING_BASELINE_ONLY",
              "period_start": manifest["quality"]["period_start"],
              "period_end": manifest["quality"]["period_end"],
              "economic_rationale": "Controle de engenharia causal; não operacionaliza H1-M/H1-R.",
              "scientific_decision": "INCONCLUSIVE", "confirmation": False}
    try:
        registry.append(experiment, "PREREGISTERED", params)
        try:
            frame, manifest = load_snapshot(snapshot)
            params["period_start"] = str(frame.timestamp.min())
            params["period_end"] = str(frame.timestamp.max())
            result = run(frame, Baseline(strategy, seed=seed), costs, policy)
            summary = write_report(output, result, manifest, params)
        except Exception as error:
            registry.append(experiment, "FAILED", {"error_type": type(error).__name__, "error": str(error)})
            raise
        registry.append(experiment, "COMPLETED", {"report_sha256": sha256(output/"summary.json"), "decision": summary["scientific_decision"], "pnl_before_tax": result["pnl_before_tax"]})
    finally:
        registry.close()
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(description="Nazaret Quant — pesquisa offline. Ordens reais indisponíveis.")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Gera fixtures e executa teste funcional")
    demo.add_argument("--output", type=Path, required=True)
    imp = sub.add_parser("ingest")
    imp.add_argument("source", type=Path)
    imp.add_argument("--provenance", type=Path, required=True)
    imp.add_argument("--output", type=Path, required=True)
    bt = sub.add_parser("backtest")
    bt.add_argument("snapshot", type=Path)
    bt.add_argument("--output", type=Path, required=True)
    bt.add_argument("--experiment", required=True)
    bt.add_argument("--strategy", choices=["no_trade", "momentum", "reversal", "random"], required=True)
    bt.add_argument("--seed", type=int, default=20261030)
    bt.add_argument("--scenario", choices=["base", "adverse"], default="base")
    bt.add_argument("--costs", type=Path, default=Path("config/costs.yaml"))
    cm = sub.add_parser("cost-map")
    cm.add_argument("snapshot", type=Path)
    cm.add_argument("--costs", type=Path, default=Path("config/costs.yaml"))
    pw = sub.add_parser("power")
    pw.add_argument("--sigma", type=float, required=True)
    pw.add_argument("--n-effective", type=int, required=True)
    pw.add_argument("--comparisons", type=int, default=4)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            snapshot = generate_demo(args.output)
            summaries = []
            for strategy in ("no_trade", "momentum", "reversal", "random"):
                summaries.append(execute(snapshot, args.output/"reports"/strategy, strategy,
                    "SYNTH-"+strategy, 20261030, "base", Path("config/costs.yaml")))
            print(json.dumps({"status": "SYNTHETIC_FUNCTIONAL_TEST_ONLY", "runs": len(summaries), "live_trading": "BLOCKED"}))
        elif args.command == "ingest":
            print(json.dumps(ingest(args.source, args.output, json.loads(args.provenance.read_text())), indent=2))
        elif args.command == "backtest":
            summary = execute(args.snapshot, args.output, args.strategy, args.experiment, args.seed, args.scenario, args.costs)
            print(json.dumps({"decision": summary["scientific_decision"], "synthetic": summary["synthetic"], "live_trading": "BLOCKED"}))
        elif args.command == "cost-map":
            frame, _ = load_snapshot(args.snapshot)
            costs = Costs(**yaml.safe_load(args.costs.read_text())["base"])
            print(json.dumps(cost_map(frame, costs), indent=2))
        else:
            print(json.dumps({"mde_approx": mde(args.sigma, args.n_effective, args.comparisons),
                "warning": "Aproximação normal; n efetivo é fornecido, não estimado. Não é o teste definitivo de poder."}))
    except (ValueError, PermissionError, FileExistsError, FileNotFoundError, KeyError) as e:
        parser.exit(2, f"Bloqueado: {e}\n")

if __name__ == "__main__":
    main()
