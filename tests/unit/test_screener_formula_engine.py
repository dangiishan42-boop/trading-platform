from __future__ import annotations

from app.services.screener.formula_engine import evaluate_formula, validate_formula


def test_validate_simple_formula():
    result = validate_formula("RSI14 < 30")
    assert result.valid is True
    assert result.referenced_metrics == ["RSI14"]


def test_validate_and_formula():
    result = validate_formula("RSI14 < 30 AND Hammer == true")
    assert result.valid is True
    assert result.referenced_metrics == ["Hammer", "RSI14"]


def test_validate_parentheses():
    result = validate_formula("RSI14 < 30 AND (Hammer == true OR BullishEngulfing == true)")
    assert result.valid is True
    assert result.referenced_metrics == ["BullishEngulfing", "Hammer", "RSI14"]


def test_reject_unknown_metric():
    result = validate_formula("MadeUpMetric > 1")
    assert result.valid is False
    assert "Unknown metric" in result.errors[0]


def test_reject_unsupported_function_period():
    result = validate_formula("EMA(13) > 100")
    assert result.valid is False
    assert "Only EMA/SMA 20,50,200 and RSI(14)" in result.errors[0]


def test_evaluate_numeric_comparison():
    assert evaluate_formula("RSI14 < 30", {"rsi_14": 24.5}) is True


def test_evaluate_boolean_comparison():
    assert evaluate_formula("Hammer == true", {"hammer": True}) is True


def test_evaluate_string_comparison():
    assert evaluate_formula('CandlestickBias == "Bullish"', {"candlestick_bias": "Bullish"}) is True


def test_missing_metric_returns_false():
    assert evaluate_formula("RSI14 < 30", {"rsi_14": None}) is False


def test_function_aliases_normalize_and_evaluate():
    result = validate_formula("RSI(14) < 30 AND Close > EMA(20)")
    assert result.valid is True
    assert result.normalized_expression == "RSI14 < 30 AND Close > EMA20"
