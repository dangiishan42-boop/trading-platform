class TradeManager:
    def summarize(self, trades: list[dict]) -> dict:
        return {"count": len(trades), "net_pnl": round(sum(t["pnl"] for t in trades), 2)}
