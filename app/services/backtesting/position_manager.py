class PositionManager:
    def quantity_for_cash(self, cash: float, price: float) -> int:
        return max(int(cash // price), 0)
