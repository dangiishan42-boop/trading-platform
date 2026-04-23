class ChargesModel:
    def total(self, turnover: float, commission_pct: float) -> float:
        return max(turnover, 0.0) * commission_pct / 100
