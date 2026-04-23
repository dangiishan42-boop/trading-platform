class PerformanceService:
    def summary(self, metrics: dict) -> dict:
        return {"return_pct": metrics.get("total_return_pct", 0.0), "win_rate_pct": metrics.get("win_rate_pct", 0.0)}
