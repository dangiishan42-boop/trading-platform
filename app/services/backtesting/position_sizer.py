from app.services.backtesting.brokerage import BrokerageModel
from app.services.backtesting.order_simulator import OrderSimulator


class PositionSizer:
    def __init__(self, brokerage_model: BrokerageModel, order_simulator: OrderSimulator) -> None:
        self.brokerage_model = brokerage_model
        self.order_simulator = order_simulator

    def entry_costs(
        self,
        quantity: int,
        reference_price: float,
        commission_pct: float,
        slippage_pct: float,
    ) -> dict | None:
        if quantity <= 0 or reference_price <= 0:
            return None

        order = self.order_simulator.market_order(reference_price, quantity, "buy", slippage_pct)
        turnover = order["fill_price"] * quantity
        brokerage = self.brokerage_model.commission(turnover, commission_pct)
        total_cash_required = turnover + brokerage
        return {
            "reference_price": reference_price,
            "fill_price": order["fill_price"],
            "turnover": turnover,
            "brokerage": brokerage,
            "slippage_cost": order["slippage_cost"],
            "total_cash_required": total_cash_required,
        }

    def size_entry(
        self,
        cash: float,
        equity: float,
        reference_price: float,
        commission_pct: float,
        slippage_pct: float,
        position_sizing_mode: str,
        fixed_quantity: int | None = None,
        capital_per_trade: float | None = None,
        equity_pct_per_trade: float | None = None,
    ) -> dict:
        normalized_mode = (position_sizing_mode or "percent_equity").strip().lower()
        empty_plan = {
            "mode": normalized_mode,
            "quantity": 0,
            "capital_budget": 0.0,
            "entry_costs": None,
        }

        if cash <= 0 or equity <= 0 or reference_price <= 0:
            return empty_plan

        if normalized_mode == "fixed_quantity":
            quantity = int(fixed_quantity or 0)
            if quantity <= 0:
                return empty_plan

            entry_costs = self.entry_costs(quantity, reference_price, commission_pct, slippage_pct)
            if not entry_costs:
                return empty_plan

            if entry_costs["total_cash_required"] > cash:
                return empty_plan

            return {
                "mode": normalized_mode,
                "quantity": quantity,
                "capital_budget": entry_costs["total_cash_required"],
                "entry_costs": entry_costs,
            }

        if normalized_mode == "fixed_capital":
            capital_budget = min(float(capital_per_trade or 0.0), cash)
        else:
            equity_fraction = float(equity_pct_per_trade or 0.0) / 100
            capital_budget = min(equity * equity_fraction, cash)

        if capital_budget <= 0:
            return empty_plan

        quantity = self._quantity_for_budget(
            capital_budget,
            reference_price,
            commission_pct,
            slippage_pct,
        )
        if quantity <= 0:
            return {
                "mode": normalized_mode,
                "quantity": 0,
                "capital_budget": capital_budget,
                "entry_costs": None,
            }

        entry_costs = self.entry_costs(quantity, reference_price, commission_pct, slippage_pct)
        while quantity > 0 and entry_costs and entry_costs["total_cash_required"] > capital_budget:
            quantity -= 1
            entry_costs = self.entry_costs(quantity, reference_price, commission_pct, slippage_pct)

        if quantity <= 0 or not entry_costs:
            return {
                "mode": normalized_mode,
                "quantity": 0,
                "capital_budget": capital_budget,
                "entry_costs": None,
            }

        return {
            "mode": normalized_mode,
            "quantity": quantity,
            "capital_budget": capital_budget,
            "entry_costs": entry_costs,
        }

    def _quantity_for_budget(
        self,
        capital_budget: float,
        reference_price: float,
        commission_pct: float,
        slippage_pct: float,
    ) -> int:
        if capital_budget <= 0 or reference_price <= 0:
            return 0

        unit_costs = self.entry_costs(1, reference_price, commission_pct, slippage_pct)
        if not unit_costs or unit_costs["total_cash_required"] <= 0:
            return 0

        quantity = int(capital_budget // unit_costs["total_cash_required"])
        return max(quantity, 0)
