import pandas as pd

from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.engine import BacktestEngine


def test_backtest_engine_applies_percent_equity_sizing_with_brokerage_and_slippage():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Close": 110.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=1.0,
        slippage_pct=1.0,
        position_sizing_mode="percent_equity",
        equity_pct_per_trade=100.0,
    )

    assert len(result["trades"]) == 1

    trade = result["trades"][0]

    assert trade["exit_reason"] == "signal"
    assert trade["position_sizing_mode"] == "percent_equity"
    assert trade["quantity"] == 9
    assert trade["capital_used"] == 918.09
    assert trade["entry_price"] == 101.0
    assert trade["exit_price"] == 108.9
    assert trade["gross_pnl"] == 90.0
    assert trade["brokerage_cost"] == 18.89
    assert trade["slippage_cost"] == 18.9
    assert trade["pnl"] == 52.21
    assert trade["return_pct"] == 5.69
    assert result["ending_equity"] == 1052.21

    metrics = MetricsService().calculate(1000, result["ending_equity"], result["trades"], result["equity_curve"])

    assert metrics["total_return_pct"] == 5.22
    assert metrics["win_rate_pct"] == 100.0
    assert metrics["total_brokerage"] == 18.89
    assert metrics["total_slippage"] == 18.9
    assert metrics["total_costs"] == 37.79


def test_backtest_engine_uses_fixed_capital_budget_for_each_trade():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Close": 110.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_capital",
        capital_per_trade=250.0,
    )

    trade = result["trades"][0]

    assert trade["exit_reason"] == "signal"
    assert trade["position_sizing_mode"] == "fixed_capital"
    assert trade["quantity"] == 2
    assert trade["capital_used"] == 200.0
    assert trade["pnl"] == 20.0
    assert trade["return_pct"] == 10.0
    assert result["ending_equity"] == 1020.0


def test_backtest_engine_uses_fixed_quantity_when_affordable():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Close": 110.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_quantity",
        fixed_quantity=3,
    )

    trade = result["trades"][0]

    assert trade["exit_reason"] == "signal"
    assert trade["position_sizing_mode"] == "fixed_quantity"
    assert trade["quantity"] == 3
    assert trade["capital_used"] == 300.0
    assert trade["pnl"] == 30.0
    assert result["ending_equity"] == 1030.0


def test_backtest_engine_skips_fixed_quantity_trade_when_cash_is_insufficient():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Close": 110.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=250,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_quantity",
        fixed_quantity=3,
    )

    assert result["trades"] == []
    assert result["ending_equity"] == 250.0


def test_backtest_engine_exits_at_stop_loss_before_signal():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Open": 99.0, "High": 101.0, "Low": 94.0, "Close": 97.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_quantity",
        fixed_quantity=1,
        stop_loss_pct=5.0,
    )

    trade = result["trades"][0]

    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == 95.0
    assert trade["pnl"] == -5.0
    assert result["ending_equity"] == 995.0


def test_backtest_engine_exits_at_take_profit_before_signal():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Open": 101.0, "High": 106.0, "Low": 100.0, "Close": 104.0, "buy_signal": False, "sell_signal": True},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_quantity",
        fixed_quantity=1,
        take_profit_pct=5.0,
    )

    trade = result["trades"][0]

    assert trade["exit_reason"] == "take_profit"
    assert trade["exit_price"] == 105.0
    assert trade["slippage_cost"] == 0.0
    assert trade["pnl"] == 5.0


def test_backtest_engine_uses_conservative_stop_when_stop_and_take_profit_hit_same_bar():
    frame = pd.DataFrame(
        [
            {"Date": "2024-01-01", "Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "buy_signal": True, "sell_signal": False},
            {"Date": "2024-01-02", "Open": 100.0, "High": 106.0, "Low": 94.0, "Close": 102.0, "buy_signal": False, "sell_signal": False},
        ]
    )

    result = BacktestEngine().run(
        frame,
        initial_capital=1000,
        commission_pct=0.0,
        slippage_pct=0.0,
        position_sizing_mode="fixed_quantity",
        fixed_quantity=1,
        stop_loss_pct=5.0,
        take_profit_pct=5.0,
    )

    trade = result["trades"][0]

    assert trade["exit_reason"] == "stop_loss"
    assert trade["exit_price"] == 95.0
    assert trade["pnl"] == -5.0
