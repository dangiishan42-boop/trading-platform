from app.services.backtesting.fill_logic import FillLogic
from app.services.backtesting.slippage import SlippageModel


class OrderSimulator:
    def __init__(self) -> None:
        self.fill_logic = FillLogic()
        self.slippage_model = SlippageModel()

    def market_order(self, price: float, quantity: int, side: str, slippage_pct: float) -> dict:
        fill_price = self.fill_logic.apply_slippage(price, slippage_pct, side)
        slippage_cost = self.slippage_model.cost(price, fill_price, quantity)
        return {
            "reference_price": price,
            "fill_price": fill_price,
            "quantity": quantity,
            "slippage_cost": slippage_cost,
            "status": "FILLED",
            "side": side,
        }

    def limit_order(self, price: float, quantity: int, side: str) -> dict:
        return {
            "reference_price": price,
            "fill_price": price,
            "quantity": quantity,
            "slippage_cost": 0.0,
            "status": "FILLED",
            "side": side,
        }
