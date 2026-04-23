from app.services.backtesting.slippage import SlippageModel


class FillLogic:
    def __init__(self) -> None:
        self.slippage_model = SlippageModel()

    def apply_slippage(self, price: float, slippage_pct: float, side: str) -> float:
        slippage_value = self.slippage_model.estimate(price, slippage_pct)
        normalized_side = side.strip().lower()

        if normalized_side == "buy":
            return price + slippage_value
        if normalized_side == "sell":
            return max(price - slippage_value, 0.0)
        raise ValueError(f"Unsupported side for slippage: {side}")
