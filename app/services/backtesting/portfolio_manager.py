class PortfolioManager:
    def equity(self, cash: float, price: float, qty: int) -> float:
        return cash + price * qty
