class MetricsService:
    def calculate(self, initial_capital: float, ending_equity: float, trades: list[dict], equity_curve: list[dict]) -> dict:
        total_trades = len(trades)
        wins = sum(1 for trade in trades if trade["pnl"] > 0)
        win_rate = (wins / total_trades * 100) if total_trades else 0.0
        total_brokerage = sum(float(trade.get("brokerage_cost", 0.0)) for trade in trades)
        total_slippage = sum(float(trade.get("slippage_cost", 0.0)) for trade in trades)
        total_costs = total_brokerage + total_slippage
        max_equity = 0.0
        max_drawdown = 0.0
        for point in equity_curve:
            equity = point["equity"]
            max_equity = max(max_equity, equity)
            if max_equity > 0:
                drawdown = ((max_equity - equity) / max_equity) * 100
                max_drawdown = max(max_drawdown, drawdown)
        net_profit = ending_equity - initial_capital
        total_return_pct = (net_profit / initial_capital) * 100 if initial_capital else 0.0
        return {
            "total_return_pct": round(total_return_pct, 2),
            "net_profit": round(net_profit, 2),
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "ending_equity": round(ending_equity, 2),
            "total_brokerage": round(total_brokerage, 2),
            "total_slippage": round(total_slippage, 2),
            "total_costs": round(total_costs, 2),
        }
