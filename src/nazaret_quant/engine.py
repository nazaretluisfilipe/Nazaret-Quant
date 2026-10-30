"""Motor de eventos OHLCV long-only. Nenhum envio de ordens reais."""
from dataclasses import dataclass
from datetime import time
from decimal import ROUND_FLOOR
import pandas as pd
from .data import validate
from .ledger import Costs, D, Ledger, money

@dataclass(frozen=True)
class Policy:
    capital: float = 250
    max_exposure: float = 150
    reserve: float = 100
    daily_loss_trigger: float = 5
    total_loss_trigger: float = 20
    horizon_minutes: int = 30
    max_signal_age_minutes: int = 5
    entry_start: str = "10:00"
    last_entry: str = "16:00"
    liquidation_after: str = "16:30"
    max_participation: float = 0.01

    def __post_init__(self):
        for k in ("capital", "max_exposure", "reserve", "daily_loss_trigger", "total_loss_trigger"):
            if D(getattr(self, k)) < 0:
                raise ValueError("Política negativa")
        if not 0 < self.capital <= 250 or self.max_exposure + self.reserve > self.capital:
            raise ValueError("Orçamento excedido")
        if min(self.horizon_minutes, self.max_signal_age_minutes) <= 0 or not 0 < self.max_participation <= 1:
            raise ValueError("Horizonte/participação inválidos")
        if not time.fromisoformat(self.entry_start) < time.fromisoformat(self.last_entry) < time.fromisoformat(self.liquidation_after):
            raise ValueError("Horários inválidos")

def run(frame, strategy, costs=Costs(), policy=Policy()):
    f, quality = validate(frame)
    # MVP H1 apenas; frequência diária precisa de calendário e corporativos.
    if ((f.timestamp - f.bar_open).dt.total_seconds() != 300).any():
        raise ValueError("Motor v0.1 suporta somente barras de cinco minutos")
    if ((f.bar_open.dt.minute % 5 != 0) | (f.bar_open.dt.second != 0) |
        (f.bar_open.dt.microsecond != 0) | (f.bar_open.dt.nanosecond != 0)).any():
        raise ValueError("Barras devem estar alinhadas na grade de cinco minutos")
    ledger = Ledger(policy.capital)
    histories, pending, entries, marks = {}, {}, {}, {}
    curve, alerts, decisions = [], [], []
    permanent_halt = False
    current_session, day_initial, daily_halt = None, None, False

    def exposure():
        return sum(money(D(marks[s]) * q) for s, q in ledger.positions.items() if q)

    def fill(row, side, qty, reason):
        price = costs.fill(row.open, side)
        fees = costs.fee(money(price * qty))
        ledger.execute(f"SIM-{len(ledger.events)+1:08d}", row.bar_open, row.symbol, side, int(qty), price, fees)
        decisions.append({"timestamp": str(row.bar_open), "symbol": row.symbol, "action": side, "reason": reason})

    def update_triggers():
        nonlocal permanent_halt, daily_halt
        equity = ledger.equity(marks)
        if ledger.initial - equity >= D(policy.total_loss_trigger):
            permanent_halt = True
        if day_initial - equity >= D(policy.daily_loss_trigger):
            daily_halt = True

    # Processa aberturas de todos os ativos antes de revelar qualquer fechamento do lote.
    for opening, group in f.groupby("bar_open", sort=True):
        rows = list(group.sort_values("symbol").itertuples(index=False))
        session = rows[0].session
        if session != current_session:
            for s, q in ledger.positions.items():
                if q:
                    alerts.append({"type": "overnight", "symbol": s, "session": session, "qty": q})
            current_session = session
            # Base do dia no último patrimônio conhecido; gap seguinte conta no gatilho.
            day_initial = ledger.equity(marks)
            daily_halt = False
            histories = {}
        for row in rows:
            marks[row.symbol] = row.open
        update_triggers()
        for row in rows:
            s, now = row.symbol, row.bar_open
            local_time = now.tz_convert("America/Sao_Paulo").time()
            held = ledger.positions.get(s, 0)
            entry = entries.get(s)
            exit_due = held and (permanent_halt or daily_halt or
                now - entry["time"] >= pd.Timedelta(minutes=policy.horizon_minutes) or
                session != entry["session"] or local_time >= time.fromisoformat(policy.liquidation_after))
            if exit_due:
                # Volume da barra que vai fechar ainda não é conhecido. Executabilidade
                # é proxy limitada; zero volume impede fill, não cria liquidez fictícia.
                if row.volume <= 0:
                    alerts.append({"type": "exit_unfilled", "symbol": s, "timestamp": str(now)})
                else:
                    capacity = int(D(row.volume) * D(policy.max_participation))
                    qty = min(held, capacity)
                    if qty:
                        price = costs.fill(row.open, "SELL")
                        if ledger.cash + money(price * qty) >= costs.fee(money(price * qty)):
                            fill(row, "SELL", qty, "horizon_session_or_loss")
                            if qty == held:
                                entries.pop(s)
                        else:
                            alerts.append({"type": "exit_fee_uncovered", "symbol": s, "timestamp": str(now)})
                    else:
                        alerts.append({"type": "exit_unfilled", "symbol": s, "timestamp": str(now)})
                pending.pop(s, None)
                continue
            proposal = pending.pop(s, None)
            if not proposal or held or permanent_halt or daily_halt:
                continue
            if proposal["session"] != session or now < proposal["known_at"] or now - proposal["known_at"] > pd.Timedelta(minutes=policy.max_signal_age_minutes):
                decisions.append({"timestamp": str(now), "symbol": s, "action": "REJECT", "reason": "stale_signal"})
                continue
            if not time.fromisoformat(policy.entry_start) <= local_time <= time.fromisoformat(policy.last_entry):
                continue
            price = costs.fill(row.open, "BUY")
            budget = min(ledger.cash - D(policy.reserve), D(policy.max_exposure) - exposure())
            qty = max(0, int((budget / price).to_integral_value(rounding=ROUND_FLOOR)))
            # Quantidade limitada pelo volume da barra anterior conhecida, sem olhar futuro.
            qty = min(qty, int(D(proposal["volume"]) * D(policy.max_participation)))
            # Proxy de preenchimento: não executar além da participação simulada
            # na barra alvo. Não é informação disponível ao formar a ordem.
            qty = min(qty, int(D(row.volume) * D(policy.max_participation)))
            while qty and money(price * qty) + costs.fee(money(price * qty)) > budget:
                qty -= 1
            if qty and row.volume > 0:
                # O veto de volume zero da barra executada é uma simplificação ex post
                # de execução, nunca um recurso do sinal; reportado como limitação.
                fill(row, "BUY", qty, "previous_closed_bar")
                marks[s] = row.open
                entries[s] = {"time": now, "session": session}
                update_triggers()
        # Só agora as barras fechadas são disponibilizadas às estratégias.
        closing = group.timestamp.max()
        for row in rows:
            marks[row.symbol] = row.close
            histories.setdefault(row.symbol, []).append(float(row.close))
            if strategy.signal(histories[row.symbol]):
                pending[row.symbol] = {"known_at": row.timestamp, "session": row.session, "volume": row.volume}
        update_triggers()
        equity = ledger.equity(marks)
        curve.append({"timestamp": str(closing), "session": session, "cash": float(ledger.cash),
                      "exposure": float(exposure()), "equity": float(equity),
                      "daily_halt": daily_halt, "permanent_halt": permanent_halt})
    for s, q in ledger.positions.items():
        if q:
            alerts.append({"type": "unliquidated_final_position", "symbol": s, "qty": q})
    ledger.reconcile()
    equity = ledger.equity(marks)
    return {"curve": curve, "fills": ledger.events, "decisions": decisions, "alerts": alerts,
            "final_cash": float(ledger.cash), "final_equity": float(equity),
            "pnl_before_tax": float(equity - ledger.initial), "positions": ledger.positions,
            "quality": quality, "live_trading": "BLOCKED",
            "execution_model": "market_next_open_proxy",
            "limitations": ["OHLCV não comprova preenchimento nem spread real.",
                "Volume executado é proxy ex post para simular ausência/limite de liquidez.",
                "Sem leilões, corporativos, tributos, book, ticks ou calendário B3 certificado.",
                "Gatilhos de perdas podem ser excedidos; marcação de posição aberta não é lucro realizado."]}
