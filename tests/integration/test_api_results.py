from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_export_latest_result_csv_includes_summary_and_trade_list():
    backtest_response = client.post(
        "/api/v1/backtest/run",
        json={
            "source": "sample",
            "symbol": "DEMO",
            "timeframe": "1D",
            "strategy_name": "ema_crossover",
            "initial_capital": 100000,
            "commission_pct": 0.1,
            "slippage_pct": 0.05,
            "stop_loss_pct": 2.0,
            "take_profit_pct": 4.0,
            "position_sizing_mode": "fixed_quantity",
            "fixed_quantity": 10,
            "parameters": {
                "fast_period": 20,
                "slow_period": 50,
            },
        },
    )

    assert backtest_response.status_code == 200

    backtest_payload = backtest_response.json()

    export_response = client.post(
        "/api/v1/results/export-csv",
        json={
            "strategy_name": backtest_payload["strategy_name"],
            "symbol": backtest_payload["symbol"],
            "timeframe": backtest_payload["timeframe"],
            "commission_pct": backtest_payload["commission_pct"],
            "slippage_pct": backtest_payload["slippage_pct"],
            "stop_loss_pct": backtest_payload["stop_loss_pct"],
            "take_profit_pct": backtest_payload["take_profit_pct"],
            "position_sizing_mode": backtest_payload["position_sizing_mode"],
            "fixed_quantity": backtest_payload["fixed_quantity"],
            "capital_per_trade": backtest_payload["capital_per_trade"],
            "equity_pct_per_trade": backtest_payload["equity_pct_per_trade"],
            "metrics": backtest_payload["metrics"],
            "trades": backtest_payload["trades"],
        },
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in export_response.headers["content-disposition"]

    content = export_response.text

    assert "Summary" in content
    assert "Trade List" in content
    assert "Strategy Name,ema_crossover" in content
    assert "Symbol,DEMO" in content
    assert "Commission %,0.1" in content
    assert "Slippage %,0.05" in content
    assert "Stop Loss %,2.0" in content
    assert "Take Profit %,4.0" in content
    assert "Position Sizing Mode,fixed_quantity" in content
    assert "Fixed Quantity,10" in content
    assert "Total Brokerage" in content
    assert "Total Slippage" in content
    assert "Total Costs" in content
    assert "Total Return %" in content
    assert "Entry Date,Exit Date,Exit Reason,Sizing Mode,Entry Price,Exit Price,Quantity,Capital Used,Gross PnL,Brokerage,Slippage,PnL,Return %" in content
