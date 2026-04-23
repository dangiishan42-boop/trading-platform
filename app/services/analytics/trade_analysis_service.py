class TradeAnalysisService:
    def pnl_distribution(self, trades: list[dict]) -> dict:
        return {"positive": sum(1 for t in trades if t["pnl"] > 0), "negative": sum(1 for t in trades if t["pnl"] <= 0)}
