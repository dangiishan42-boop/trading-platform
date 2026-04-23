import pandas as pd

from app.services.backtesting.brokerage import BrokerageModel
from app.services.backtesting.order_simulator import OrderSimulator
from app.services.backtesting.position_sizer import PositionSizer
from app.services.backtesting.risk_manager import RiskManager


class BacktestEngine:
    def __init__(self) -> None:
        self.brokerage_model = BrokerageModel()
        self.order_simulator = OrderSimulator()
        self.position_sizer = PositionSizer(self.brokerage_model, self.order_simulator)
        self.risk_manager = RiskManager()

    def _price_from_row(self, row: pd.Series, column_name: str, fallback: float) -> float:
        value = row.get(column_name, fallback)
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(fallback)

    def _exit_trade(
        self,
        reference_price: float,
        quantity: int,
        commission_pct: float,
        slippage_pct: float,
        execution_style: str,
    ) -> dict:
        if execution_style == "limit":
            order = self.order_simulator.limit_order(reference_price, quantity, "sell")
        else:
            order = self.order_simulator.market_order(reference_price, quantity, "sell", slippage_pct)

        turnover = order["fill_price"] * quantity
        brokerage = self.brokerage_model.commission(turnover, commission_pct)
        proceeds = turnover - brokerage
        return {
            "reference_price": reference_price,
            "fill_price": order["fill_price"],
            "turnover": turnover,
            "brokerage": brokerage,
            "slippage_cost": order["slippage_cost"],
            "proceeds": proceeds,
        }

    def _close_position(
        self,
        cash: float,
        active_position: dict,
        exit_reference_price: float,
        exit_time: str,
        commission_pct: float,
        slippage_pct: float,
        exit_reason: str,
        execution_style: str,
    ) -> tuple[float, dict]:
        quantity = active_position["quantity"]
        exit_costs = self._exit_trade(
            exit_reference_price,
            quantity,
            commission_pct,
            slippage_pct,
            execution_style,
        )
        gross_pnl = quantity * (exit_reference_price - active_position["entry_reference_price"])
        brokerage_cost = active_position["entry_brokerage"] + exit_costs["brokerage"]
        slippage_cost = active_position["entry_slippage"] + exit_costs["slippage_cost"]
        pnl = gross_pnl - brokerage_cost - slippage_cost
        trade = {
            "entry_time": active_position["entry_time"],
            "exit_time": exit_time,
            "entry_price": round(active_position["entry_fill_price"], 2),
            "exit_price": round(exit_costs["fill_price"], 2),
            "exit_reason": exit_reason,
            "position_sizing_mode": active_position["position_sizing_mode"],
            "quantity": quantity,
            "capital_used": round(active_position["capital_used"], 2),
            "gross_pnl": round(gross_pnl, 2),
            "brokerage_cost": round(brokerage_cost, 2),
            "slippage_cost": round(slippage_cost, 2),
            "pnl": round(pnl, 2),
            "return_pct": round((pnl / active_position["capital_used"]) * 100, 2) if active_position["capital_used"] else 0.0,
        }
        return cash + exit_costs["proceeds"], trade

    def run(
        self,
        df: pd.DataFrame,
        initial_capital: float,
        commission_pct: float,
        slippage_pct: float = 0.0,
        position_sizing_mode: str = "percent_equity",
        fixed_quantity: int | None = None,
        capital_per_trade: float | None = None,
        equity_pct_per_trade: float | None = 100.0,
        stop_loss_pct: float | None = None,
        take_profit_pct: float | None = None,
    ) -> dict:
        cash = float(initial_capital)
        active_position: dict | None = None
        trades: list[dict] = []
        equity_curve: list[dict] = []

        for bar_index, (_, row) in enumerate(df.iterrows()):
            close_price = self._price_from_row(row, "Close", 0.0)
            open_price = self._price_from_row(row, "Open", close_price)
            high_price = self._price_from_row(row, "High", close_price)
            low_price = self._price_from_row(row, "Low", close_price)
            timestamp = str(row["Date"])

            if active_position is not None and bar_index > active_position["entry_bar_index"]:
                risk_exit = self.risk_manager.evaluate_long_exit(
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    stop_loss_price=active_position["stop_loss_price"],
                    take_profit_price=active_position["take_profit_price"],
                )
                if risk_exit is not None:
                    cash, trade = self._close_position(
                        cash,
                        active_position,
                        float(risk_exit["reference_price"]),
                        timestamp,
                        commission_pct,
                        slippage_pct,
                        str(risk_exit["reason"]),
                        str(risk_exit["execution_style"]),
                    )
                    trades.append(trade)
                    active_position = None

            current_equity = cash + (active_position["quantity"] * close_price if active_position else 0.0)

            if bool(row.get("buy_signal", False)) and active_position is None:
                sizing_plan = self.position_sizer.size_entry(
                    cash=cash,
                    equity=current_equity,
                    reference_price=close_price,
                    commission_pct=commission_pct,
                    slippage_pct=slippage_pct,
                    position_sizing_mode=position_sizing_mode,
                    fixed_quantity=fixed_quantity,
                    capital_per_trade=capital_per_trade,
                    equity_pct_per_trade=equity_pct_per_trade,
                )
                entry_costs = sizing_plan["entry_costs"]
                if sizing_plan["quantity"] > 0 and entry_costs:
                    cash -= entry_costs["total_cash_required"]
                    risk_levels = self.risk_manager.levels(
                        entry_costs["fill_price"],
                        stop_loss_pct,
                        take_profit_pct,
                    )
                    active_position = {
                        "entry_bar_index": bar_index,
                        "entry_reference_price": close_price,
                        "entry_fill_price": entry_costs["fill_price"],
                        "entry_brokerage": entry_costs["brokerage"],
                        "entry_slippage": entry_costs["slippage_cost"],
                        "entry_time": timestamp,
                        "position_sizing_mode": sizing_plan["mode"],
                        "quantity": sizing_plan["quantity"],
                        "capital_used": entry_costs["total_cash_required"],
                        "stop_loss_price": risk_levels["stop_loss_price"],
                        "take_profit_price": risk_levels["take_profit_price"],
                    }

            elif bool(row.get("sell_signal", False)) and active_position is not None:
                cash, trade = self._close_position(
                    cash,
                    active_position,
                    close_price,
                    timestamp,
                    commission_pct,
                    slippage_pct,
                    "signal",
                    "market",
                )
                trades.append(trade)
                active_position = None

            equity = cash + (active_position["quantity"] * close_price if active_position else 0.0)
            equity_curve.append({"timestamp": timestamp, "equity": round(equity, 2)})

        if active_position is not None:
            last_close = self._price_from_row(df.iloc[-1], "Close", 0.0)
            exit_time = str(df.iloc[-1]["Date"])
            cash, trade = self._close_position(
                cash,
                active_position,
                last_close,
                exit_time,
                commission_pct,
                slippage_pct,
                "end_of_data",
                "market",
            )
            trades.append(trade)
            equity_curve[-1]["equity"] = round(cash, 2)

        return {"trades": trades, "equity_curve": equity_curve, "ending_equity": round(cash, 2)}
