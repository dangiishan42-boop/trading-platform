class BrokerageModel:
    def commission(self, turnover: float, pct: float) -> float:
        return max(turnover, 0.0) * pct / 100
