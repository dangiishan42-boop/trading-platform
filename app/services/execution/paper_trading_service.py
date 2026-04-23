class PaperTradingService:
    def place_order(self, symbol: str, side: str, quantity: int) -> dict:
        return {"symbol": symbol, "side": side, "quantity": quantity, "status": "paper_filled"}
