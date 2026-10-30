"""Baselines causais: recebem somente fechamentos já observados."""
import random

class Baseline:
    def __init__(self, kind="no_trade", lookback=3, seed=20261030, probability=0.1):
        if kind not in {"no_trade", "momentum", "reversal", "random"}:
            raise ValueError("Baseline desconhecido")
        if type(lookback) is not int or lookback < 1 or not 0 <= probability <= 1:
            raise ValueError("Parâmetros inválidos")
        self.kind, self.lookback = kind, lookback
        self.rng = random.Random(seed)
        self.probability = probability

    def signal(self, history):
        if self.kind == "no_trade" or len(history) <= self.lookback:
            return False
        if self.kind == "random":
            return self.rng.random() < self.probability
        ret = history[-1] / history[-1-self.lookback] - 1
        return ret > 0 if self.kind == "momentum" else ret < 0
