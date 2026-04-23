class SlippageModel:
    def estimate(self, price: float, pct: float = 0.05) -> float:
        return price * pct / 100

    def cost(self, reference_price: float, fill_price: float, quantity: int) -> float:
        return abs(fill_price - reference_price) * quantity
