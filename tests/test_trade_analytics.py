"""Offline-only accounting checks: partial exits, multi-symbol and invalid fills."""
import pytest
from nazaret_quant.trade_analytics import reconstruct_closed_episodes


def fill(oid, sym, side, qty, price, fee=0):
    return {"order_id": oid, "symbol": sym, "side": side, "qty": qty,
            "price": str(price), "notional": str(round(qty*price, 2)),
            "fee": str(fee), "timestamp": "2025-01-02T10:00:00-03:00"}


def test_partial_exit_aggregates_before_win_rate_and_counts_fees_once():
    events = [
        fill("1", "AAA3", "BUY", 10, 10, 1),
        fill("2", "AAA3", "SELL", 4, 11, 0.4),
        fill("3", "AAA3", "SELL", 6, 12, 0.6),
    ]
    r = reconstruct_closed_episodes(events)
    assert r["open_episode_count"] == 0
    assert r["closed_episode_count"] == 1
    item = r["closed_episodes"][0]
    assert item["entry_orders"] == 1 and item["exit_orders"] == 2
    assert item["bought_qty"] == item["sold_qty"] == 10
    assert item["fees_brl"] == pytest.approx(2)
    assert item["pnl_after_estimated_costs_before_tax_brl"] == pytest.approx(14)
    assert r["closed_pnl_pretax_brl"] == pytest.approx(14)


def test_open_inventory_is_excluded_not_falsely_marked_as_profit():
    r = reconstruct_closed_episodes([
        fill("1", "AAA3", "BUY", 10, 10),
        fill("2", "AAA3", "SELL", 4, 11),
    ])
    assert not r["closed_episodes"]
    assert r["open_episode_count"] == 1
    assert r["open_episodes"][0]["remaining_qty"] == 6
    assert r["closed_pnl_pretax_brl"] == 0


def test_interleaved_symbols_additional_buys_and_second_episode():
    events = [
        fill("1", "AAA3", "BUY", 2, 10),
        fill("2", "BBB4", "BUY", 1, 20),
        fill("3", "AAA3", "BUY", 1, 12),
        fill("4", "AAA3", "SELL", 3, 11),
        fill("5", "AAA3", "BUY", 1, 9),
        fill("6", "AAA3", "SELL", 1, 10),
    ]
    r = reconstruct_closed_episodes(events)
    assert r["closed_episode_count"] == 2
    assert [x["pnl_after_estimated_costs_before_tax_brl"] for x in r["closed_episodes"]] == [1, 1]
    assert r["open_episodes"][0]["symbol"] == "BBB4"


def test_no_trade_not_automatically_profitable():
    r = reconstruct_closed_episodes([])
    assert r["closed_episode_count"] == 0
    assert r["closed_pnl_pretax_brl"] == 0


@pytest.mark.parametrize("events", [
    [fill("1", "AAA3", "SELL", 1, 10)],
    [fill("1", "AAA3", "BUY", 1, 10), fill("2", "AAA3", "SELL", 2, 10)],
    [fill("1", "AAA3", "BUY", 1, 10), fill("1", "BBB4", "BUY", 1, 20)],
    [{"order_id": "1", "symbol": "AAA3", "side": "BUY", "qty": True,
      "price": "10", "notional": "10", "fee": "0", "timestamp": "now"}],
    [{"order_id": "1", "symbol": "AAA3", "side": "BUY", "qty": 1,
      "price": "10", "notional": "9", "fee": "0", "timestamp": "now"}],
    [{"order_id": "1", "symbol": "AAA3", "side": "BUY", "qty": 1,
      "price": "nan", "notional": "10", "fee": "0", "timestamp": "now"}],
])
def test_corrupt_or_impossible_ledger_events_fail_closed(events):
    with pytest.raises(ValueError):
        reconstruct_closed_episodes(events)
