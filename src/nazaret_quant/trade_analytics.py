"""Conservative, offline reconstruction of fully closed simulation trade episodes.

Fills originate in the simulated ledger. A trade episode begins when a symbol's
inventory goes from 0 to positive, and closes only when it returns to zero.
Partial exits are aggregated; unresolved positions are explicitly excluded from
expectancy. Returns are PRE-TAX and rely on approximate simulation fills.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from .ledger import money


def _finite_amount(value, name):
    if isinstance(value, bool):
        raise ValueError(f"Invalid {name}")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}") from exc
    if not out.is_finite():
        raise ValueError(f"Non-finite {name}")
    return out


def reconstruct_closed_episodes(fills):
    """Return completed round trips and inventory still open; never book open P&L.

    This is FIFO-agnostic episode accounting rather than tax-lot accounting:
    concurrent add-on buys and partial exits of one symbol form ONE complete
    episode, and all entry/exit fees are included exactly once.
    """
    episodes = {}
    completed = []
    ids = set()
    for i, row in enumerate(fills):
        if not isinstance(row, dict):
            raise ValueError("Fill must be a mapping")
        oid = row.get("order_id")
        symbol = row.get("symbol")
        side = row.get("side")
        qty = row.get("qty")
        if not isinstance(oid, str) or not oid or oid in ids:
            raise ValueError("Missing or duplicate simulated order ID")
        ids.add(oid)
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError("Invalid fill symbol")
        if side not in ("BUY", "SELL") or type(qty) is not int or qty <= 0:
            raise ValueError("Invalid fill side or quantity")
        price = _finite_amount(row.get("price"), "price")
        notional = _finite_amount(row.get("notional"), "notional")
        fee = _finite_amount(row.get("fee"), "fee")
        if price <= 0 or notional <= 0 or fee < 0:
            raise ValueError("Nonpositive notional or negative fee")
        if money(price * qty) != notional:
            raise ValueError("Fill notional fails ledger rounding reconciliation")
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp:
            raise ValueError("Missing fill timestamp")
        open_episode = episodes.get(symbol)
        if side == "BUY":
            if open_episode is None:
                open_episode = {
                    "symbol": symbol, "first_buy_timestamp": timestamp,
                    "entry_orders": 0, "exit_orders": 0,
                    "bought_qty": 0, "sold_qty": 0,
                    "open_qty": 0,
                    "buy_notional": Decimal(0), "sell_notional": Decimal(0),
                    "buy_fees": Decimal(0), "sell_fees": Decimal(0),
                }
                episodes[symbol] = open_episode
            open_episode["entry_orders"] += 1
            open_episode["bought_qty"] += qty
            open_episode["open_qty"] += qty
            open_episode["buy_notional"] += notional
            open_episode["buy_fees"] += fee
        else:
            if open_episode is None or qty > open_episode["open_qty"]:
                raise ValueError("Sell exceeds held simulated inventory")
            open_episode["exit_orders"] += 1
            open_episode["sold_qty"] += qty
            open_episode["open_qty"] -= qty
            open_episode["sell_notional"] += notional
            open_episode["sell_fees"] += fee
            if open_episode["open_qty"] == 0:
                pnl = (open_episode["sell_notional"] - open_episode["buy_notional"]
                       - open_episode["buy_fees"] - open_episode["sell_fees"])
                completed.append({
                    "symbol": symbol,
                    "first_buy_timestamp": open_episode["first_buy_timestamp"],
                    "last_sell_timestamp": timestamp,
                    "bought_qty": open_episode["bought_qty"],
                    "sold_qty": open_episode["sold_qty"],
                    "entry_orders": open_episode["entry_orders"],
                    "exit_orders": open_episode["exit_orders"],
                    "buy_notional_brl": float(open_episode["buy_notional"]),
                    "sell_notional_brl": float(open_episode["sell_notional"]),
                    "fees_brl": float(open_episode["buy_fees"] + open_episode["sell_fees"]),
                    "pnl_after_estimated_costs_before_tax_brl": float(pnl),
                })
                del episodes[symbol]
    still_open = [
        {
            "symbol": sym,
            "first_buy_timestamp": x["first_buy_timestamp"],
            "remaining_qty": x["open_qty"],
            "entry_orders": x["entry_orders"],
            "partial_exit_orders": x["exit_orders"],
            "status": "EXCLUDED_FROM_CLOSED_TRADE_EXPECTANCY",
        }
        for sym, x in sorted(episodes.items())
    ]
    return {
        "status": "SIMULATION_ACCOUNTING_ONLY_PRETAX_UNCONFIRMED_COSTS",
        "closed_episodes": completed,
        "open_episodes": still_open,
        "closed_episode_count": len(completed),
        "open_episode_count": len(still_open),
        "closed_pnl_pretax_brl": float(sum(
            (Decimal(str(x["pnl_after_estimated_costs_before_tax_brl"]))
             for x in completed), Decimal(0))),
        "warnings": [
            "Closed trade episodes are NOT independent statistical observations.",
            "Costs are approximate and corporate actions/tax are not accounted for.",
            "Open and partially closed episodes do not enter closed-trade expectancy.",
            "This is not FIFO tax-lot accounting or verification of actual broker fills.",
        ],
    }
