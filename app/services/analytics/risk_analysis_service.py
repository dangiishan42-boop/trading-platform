class RiskAnalysisService:
    def exposure(self, trades: list[dict]) -> dict:
        return {"trade_count": len(trades)}
