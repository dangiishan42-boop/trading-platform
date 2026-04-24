from app.services.backtesting.portfolio_backtest_service import PortfolioBacktestService


def test_portfolio_rebalancing_changes_sleeve_weights_on_month_boundary():
    symbol_results = [
        {
            "allocation_pct": 50,
            "allocated_capital": 50,
            "equity_curve": [
                {"timestamp": "2024-01-31", "equity": 50},
                {"timestamp": "2024-02-01", "equity": 100},
                {"timestamp": "2024-02-02", "equity": 50},
            ],
        },
        {
            "allocation_pct": 50,
            "allocated_capital": 50,
            "equity_curve": [
                {"timestamp": "2024-01-31", "equity": 50},
                {"timestamp": "2024-02-01", "equity": 25},
                {"timestamp": "2024-02-02", "equity": 50},
            ],
        },
    ]

    service = PortfolioBacktestService()

    no_rebalance = service._combine_equity_curves(symbol_results, "none")
    monthly = service._combine_equity_curves(symbol_results, "monthly")
    quarterly = service._combine_equity_curves(symbol_results, "quarterly")

    assert no_rebalance[-1]["equity"] == 100
    assert monthly[-1]["equity"] == 156.25
    assert quarterly[-1]["equity"] == 100
