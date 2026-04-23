import csv
import re
from datetime import UTC, datetime
from io import StringIO

from app.schemas.backtest_schema import BacktestExportRequest


class ResultExportService:
    def build_csv(self, payload: BacktestExportRequest) -> str:
        buffer = StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["Summary"])
        writer.writerow(["Field", "Value"])

        summary_rows = [
            ("Strategy Name", payload.strategy_name),
            ("Symbol", payload.symbol),
            ("Timeframe", payload.timeframe),
            ("Commission %", payload.commission_pct),
            ("Slippage %", payload.slippage_pct),
            ("Stop Loss %", payload.stop_loss_pct if payload.stop_loss_pct is not None else "Off"),
            ("Take Profit %", payload.take_profit_pct if payload.take_profit_pct is not None else "Off"),
            ("Position Sizing Mode", payload.position_sizing_mode),
            ("Fixed Quantity", payload.fixed_quantity if payload.fixed_quantity is not None else ""),
            ("Capital Per Trade", payload.capital_per_trade if payload.capital_per_trade is not None else ""),
            ("Equity % Per Trade", payload.equity_pct_per_trade if payload.equity_pct_per_trade is not None else ""),
            ("Total Return %", payload.metrics.total_return_pct),
            ("Net Profit", payload.metrics.net_profit),
            ("Total Trades", payload.metrics.total_trades),
            ("Win Rate %", payload.metrics.win_rate_pct),
            ("Max Drawdown %", payload.metrics.max_drawdown_pct),
            ("Ending Equity", payload.metrics.ending_equity),
            ("Total Brokerage", payload.metrics.total_brokerage),
            ("Total Slippage", payload.metrics.total_slippage),
            ("Total Costs", payload.metrics.total_costs),
        ]
        writer.writerows(summary_rows)

        writer.writerow([])
        writer.writerow(["Trade List"])
        writer.writerow([
            "Entry Date",
            "Exit Date",
            "Exit Reason",
            "Sizing Mode",
            "Entry Price",
            "Exit Price",
            "Quantity",
            "Capital Used",
            "Gross PnL",
            "Brokerage",
            "Slippage",
            "PnL",
            "Return %",
        ])

        for trade in payload.trades:
            writer.writerow(
                [
                    trade.entry_time,
                    trade.exit_time,
                    trade.exit_reason,
                    trade.position_sizing_mode,
                    trade.entry_price,
                    trade.exit_price,
                    trade.quantity,
                    trade.capital_used,
                    trade.gross_pnl,
                    trade.brokerage_cost,
                    trade.slippage_cost,
                    trade.pnl,
                    trade.return_pct,
                ]
            )

        return buffer.getvalue()

    def build_filename(self, payload: BacktestExportRequest) -> str:
        strategy = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.strategy_name).strip("_") or "strategy"
        symbol = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.symbol).strip("_") or "symbol"
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"backtest_result_{strategy}_{symbol}_{timestamp}.csv"
