class DrawdownService:
    def calculate(self, equity_curve: list[dict]) -> float:
        peak = 0.0
        max_drawdown = 0.0
        for point in equity_curve:
            peak = max(peak, point["equity"])
            if peak:
                dd = (peak - point["equity"]) / peak * 100
                max_drawdown = max(max_drawdown, dd)
        return round(max_drawdown, 2)
