class RiskManager:
    def levels(self, entry_price: float, stop_loss_pct: float | None, take_profit_pct: float | None) -> dict:
        stop_loss_price = None
        take_profit_price = None

        if stop_loss_pct is not None:
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        if take_profit_pct is not None:
            take_profit_price = entry_price * (1 + take_profit_pct / 100)

        return {
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
        }

    def evaluate_long_exit(
        self,
        open_price: float,
        high_price: float,
        low_price: float,
        stop_loss_price: float | None,
        take_profit_price: float | None,
    ) -> dict | None:
        if stop_loss_price is None and take_profit_price is None:
            return None

        if stop_loss_price is not None and open_price <= stop_loss_price:
            return {
                "reason": "stop_loss",
                "execution_style": "market",
                "reference_price": open_price,
            }

        if take_profit_price is not None and open_price >= take_profit_price:
            return {
                "reason": "take_profit",
                "execution_style": "limit",
                "reference_price": open_price,
            }

        stop_loss_hit = stop_loss_price is not None and low_price <= stop_loss_price
        take_profit_hit = take_profit_price is not None and high_price >= take_profit_price

        if stop_loss_hit and take_profit_hit:
            return {
                "reason": "stop_loss",
                "execution_style": "market",
                "reference_price": stop_loss_price,
            }

        if stop_loss_hit:
            return {
                "reason": "stop_loss",
                "execution_style": "market",
                "reference_price": stop_loss_price,
            }

        if take_profit_hit:
            return {
                "reason": "take_profit",
                "execution_style": "limit",
                "reference_price": take_profit_price,
            }

        return None
