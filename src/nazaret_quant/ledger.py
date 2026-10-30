"""Contabilidade da simulação com partidas balanceadas e reconciliação."""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP

def D(value) -> Decimal:
    x = Decimal(str(value))
    if not x.is_finite():
        raise ValueError("Valor monetário não finito")
    return x

def money(value) -> Decimal:
    return D(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

@dataclass(frozen=True)
class Costs:
    half_spread_bps: float = 5.0
    slippage_bps: float = 5.0
    fee_bps: float = 3.0
    fixed_fee: float = 0.0
    confirmed: bool = False

    def __post_init__(self):
        for k in ("half_spread_bps", "slippage_bps", "fee_bps", "fixed_fee"):
            if D(getattr(self, k)) < 0:
                raise ValueError("Custo negativo")
        if D(self.half_spread_bps) + D(self.slippage_bps) >= 10000:
            raise ValueError("Atrito de execução inválido")

    def fill(self, reference, side):
        if side not in {"BUY", "SELL"}:
            raise ValueError("Lado inválido")
        impact = (D(self.half_spread_bps) + D(self.slippage_bps)) / D(10000)
        return D(reference) * (1 + impact if side == "BUY" else 1 - impact)

    def fee(self, notional):
        return money(D(notional) * D(self.fee_bps) / D(10000) + D(self.fixed_fee))

class Ledger:
    def __init__(self, capital=250):
        self.initial = money(capital)
        if self.initial <= 0:
            raise ValueError("Capital deve ser positivo")
        self.cash = self.initial
        self.positions = {}
        self.events = []
        self.order_ids = set()

    def execute(self, order_id, timestamp, symbol, side, qty, price, fee):
        if order_id in self.order_ids:
            raise ValueError("ID de ordem duplicado")
        if side not in {"BUY", "SELL"} or type(qty) is not int or qty <= 0:
            raise ValueError("Somente quantidades inteiras positivas e BUY/SELL")
        price, fee = D(price), money(fee)
        if price <= 0 or fee < 0:
            raise ValueError("Preço/taxa inválidos")
        amount = money(price * qty)
        held = self.positions.get(symbol, 0)
        if side == "BUY":
            if amount + fee > self.cash:
                raise ValueError("Caixa insuficiente: crédito proibido")
            cash_delta, security_delta = -amount - fee, amount
            new_qty = held + qty
        else:
            if qty > held:
                raise ValueError("Venda descoberta proibida")
            if self.cash + amount - fee < 0:
                raise ValueError("Taxa sem cobertura")
            cash_delta, security_delta = amount - fee, -amount
            new_qty = held - qty
        # Ativo caixa + conta transitória de títulos + despesa = 0 em cada fill.
        entries = {"cash": str(cash_delta), "securities_at_transaction": str(security_delta), "fees": str(fee)}
        assert sum(D(x) for x in entries.values()) == 0
        self.cash += cash_delta
        self.positions[symbol] = new_qty
        self.order_ids.add(order_id)
        self.events.append({"order_id": order_id, "timestamp": str(timestamp), "symbol": symbol,
                            "side": side, "qty": qty, "price": str(price), "notional": str(amount),
                            "fee": str(fee), "entries": entries})
        self.reconcile()

    def reconcile(self):
        expected_cash, expected_positions = self.initial, {}
        for e in self.events:
            sign = 1 if e["side"] == "BUY" else -1
            expected_cash -= sign * D(e["notional"]) + D(e["fee"])
            expected_positions[e["symbol"]] = expected_positions.get(e["symbol"], 0) + sign * e["qty"]
            if sum(D(x) for x in e["entries"].values()) != 0:
                raise AssertionError("Partidas não balanceadas")
        if self.cash != expected_cash or self.positions != expected_positions or self.cash < 0:
            raise AssertionError("Reconciliação falhou")

    def equity(self, marks):
        return self.cash + sum(money(D(marks[s]) * q) for s, q in self.positions.items() if q)
