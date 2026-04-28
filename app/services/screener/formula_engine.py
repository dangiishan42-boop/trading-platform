from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class FormulaValidation:
    valid: bool
    normalized_expression: str
    errors: list[str]
    referenced_metrics: list[str]


ALIAS_FIELDS: dict[str, str] = {
    "LTP": "ltp",
    "Close": "ltp",
    "Open": "candle_open",
    "High": "candle_high",
    "Low": "candle_low",
    "PrevClose": "previous_close",
    "PercentChange": "percent_change",
    "PointChange": "point_change",
    "Volume": "volume",
    "AvgVolume20D": "avg_volume_20d",
    "RelativeVolume": "relative_volume",
    "VolumeSpike": "volume_spike",
    "Turnover": "turnover",
    "GapUpPct": "gap_up_pct",
    "GapDownPct": "gap_down_pct",
    "DayRangePct": "day_range_pct",
    "DistanceFrom52WHighPct": "distance_from_52w_high_pct",
    "DistanceFrom52WLowPct": "distance_from_52w_low_pct",
    "EMA20": "ema_20",
    "EMA50": "ema_50",
    "EMA200": "ema_200",
    "SMA20": "sma_20",
    "SMA50": "sma_50",
    "SMA200": "sma_200",
    "RSI14": "rsi_14",
    "MACDLine": "macd_line",
    "MACDSignal": "macd_signal",
    "MACDHistogram": "macd_histogram",
    "MACD_Bullish": "macd_bullish",
    "MACD_Bearish": "macd_bearish",
    "PriceAboveEMA20": "price_above_ema20",
    "PriceAboveEMA50": "price_above_ema50",
    "PriceAboveEMA200": "price_above_ema200",
    "EMA20AboveEMA50": "ema20_above_ema50",
    "EMA50AboveEMA200": "ema50_above_ema200",
    "Breakout20D": "breakout_20d",
    "Breakdown20D": "breakdown_20d",
    "Breakout52W": "breakout_52w",
    "Breakdown52W": "breakdown_52w",
    "VolumeConfirmedBreakout": "volume_confirmed_breakout",
    "TrendScore": "trend_score",
    "TechnicalRating": "technical_rating",
    "Doji": "doji",
    "Hammer": "hammer",
    "ShootingStar": "shooting_star",
    "BullishEngulfing": "bullish_engulfing",
    "BearishEngulfing": "bearish_engulfing",
    "InsideBar": "inside_bar",
    "OutsideBar": "outside_bar",
    "BullishMarubozu": "bullish_marubozu",
    "BearishMarubozu": "bearish_marubozu",
    "GapUp": "gap_up",
    "GapDown": "gap_down",
    "StrongBullishCandle": "strong_bullish_candle",
    "StrongBearishCandle": "strong_bearish_candle",
    "CandlestickBias": "candlestick_bias",
}

_ALIAS_BY_LOWER = {key.lower(): key for key in ALIAS_FIELDS}
_TOKEN_RE = re.compile(
    r"""
    (?P<SPACE>\s+)
    |(?P<STRING>"[^"\\]*(?:\\.[^"\\]*)*")
    |(?P<OP>>=|<=|==|!=|>|<)
    |(?P<LPAREN>\()
    |(?P<RPAREN>\))
    |(?P<NUMBER>-?\d+(?:\.\d+)?)
    |(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    |(?P<MISMATCH>.)
    """,
    re.VERBOSE,
)
_FUNCTION_RE = re.compile(r"\b(EMA|SMA|RSI)\s*\(\s*(\d+)\s*\)", re.IGNORECASE)


@dataclass
class Token:
    kind: str
    value: Any


def normalize_aliases(expression: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1).upper()
        period = match.group(2)
        if name == "RSI" and period == "14":
            return "RSI14"
        if name in {"EMA", "SMA"} and period in {"20", "50", "200"}:
            return f"{name}{period}"
        raise ValueError("Only EMA/SMA 20,50,200 and RSI(14) are supported in v1.")

    return _FUNCTION_RE.sub(replace, str(expression or "").strip())


def validate_formula(expression: str) -> FormulaValidation:
    try:
        normalized = normalize_aliases(expression)
        tokens = _tokenize(normalized)
        parser = _Parser(tokens)
        parser.parse_expression()
        parser.expect_end()
        return FormulaValidation(True, normalized, [], sorted(parser.referenced_metrics))
    except ValueError as exc:
        normalized = str(expression or "").strip()
        try:
            normalized = normalize_aliases(expression)
        except ValueError:
            pass
        return FormulaValidation(False, normalized, [str(exc)], [])


def evaluate_formula(expression: str, row_metrics: dict[str, Any]) -> bool:
    validation = validate_formula(expression)
    if not validation.valid:
        return False
    try:
        parser = _Parser(_tokenize(validation.normalized_expression), row_metrics=row_metrics)
        return bool(parser.parse_expression())
    except ValueError:
        return False


def _tokenize(expression: str) -> list[Token]:
    if not str(expression or "").strip():
        raise ValueError("Formula expression is required.")
    tokens: list[Token] = []
    for match in _TOKEN_RE.finditer(expression):
        kind = match.lastgroup or ""
        value = match.group()
        if kind == "SPACE":
            continue
        if kind == "MISMATCH":
            raise ValueError(f"Invalid token: {value}")
        if kind == "IDENT":
            upper = value.upper()
            lower = value.lower()
            if upper in {"AND", "OR", "NOT"}:
                tokens.append(Token(upper, upper))
            elif lower in {"true", "false"}:
                tokens.append(Token("BOOL", lower == "true"))
            elif lower in _ALIAS_BY_LOWER:
                canonical = _ALIAS_BY_LOWER[lower]
                tokens.append(Token("IDENT", canonical))
            else:
                raise ValueError(f"Unknown metric: {value}")
        elif kind == "NUMBER":
            tokens.append(Token("NUMBER", float(value)))
        elif kind == "STRING":
            tokens.append(Token("STRING", bytes(value[1:-1], "utf-8").decode("unicode_escape")))
        else:
            tokens.append(Token(kind, value))
    return tokens


class _Parser:
    def __init__(self, tokens: list[Token], row_metrics: dict[str, Any] | None = None) -> None:
        self.tokens = tokens
        self.index = 0
        self.row_metrics = row_metrics
        self.referenced_metrics: set[str] = set()

    def parse_expression(self) -> Any:
        return self._parse_or()

    def expect_end(self) -> None:
        if self._peek() is not None:
            raise ValueError("Invalid syntax near end of formula.")

    def _parse_or(self) -> Any:
        left = self._parse_and()
        while self._match("OR"):
            right = self._parse_and()
            left = bool(left) or bool(right)
        return left

    def _parse_and(self) -> Any:
        left = self._parse_not()
        while self._match("AND"):
            right = self._parse_not()
            left = bool(left) and bool(right)
        return left

    def _parse_not(self) -> Any:
        if self._match("NOT"):
            return not bool(self._parse_not())
        return self._parse_comparison()

    def _parse_comparison(self) -> Any:
        left = self._parse_primary()
        token = self._peek()
        if token and token.kind == "OP":
            op = self._advance().value
            right = self._parse_primary()
            return self._compare(left, op, right)
        if self.row_metrics is None:
            return left
        return bool(left) if left is not None else False

    def _parse_primary(self) -> Any:
        token = self._peek()
        if token is None:
            raise ValueError("Invalid syntax: expected metric, literal, or parenthesis.")
        if self._match("LPAREN"):
            value = self.parse_expression()
            if not self._match("RPAREN"):
                raise ValueError("Unmatched parentheses.")
            return value
        token = self._advance()
        if token.kind in {"NUMBER", "STRING", "BOOL"}:
            return token.value
        if token.kind == "IDENT":
            self.referenced_metrics.add(token.value)
            if self.row_metrics is None:
                return token.value
            return self.row_metrics.get(ALIAS_FIELDS[token.value])
        raise ValueError("Invalid syntax: expected metric, literal, or parenthesis.")

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        if self.row_metrics is None:
            if not isinstance(left, str) and not isinstance(right, str):
                raise ValueError("Invalid comparison.")
            return False
        if left is None or right is None:
            return False
        if isinstance(left, bool) or isinstance(right, bool):
            if op not in {"==", "!="}:
                return False
            return (bool(left) == bool(right)) if op == "==" else (bool(left) != bool(right))
        if isinstance(left, str) or isinstance(right, str):
            if op not in {"==", "!="}:
                return False
            return (str(left).lower() == str(right).lower()) if op == "==" else (str(left).lower() != str(right).lower())
        try:
            left_num = float(left)
            right_num = float(right)
        except (TypeError, ValueError):
            return False
        if op == ">":
            return left_num > right_num
        if op == "<":
            return left_num < right_num
        if op == ">=":
            return left_num >= right_num
        if op == "<=":
            return left_num <= right_num
        if op == "==":
            return left_num == right_num
        if op == "!=":
            return left_num != right_num
        return False

    def _peek(self) -> Token | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def _advance(self) -> Token:
        token = self._peek()
        if token is None:
            raise ValueError("Invalid syntax: unexpected end of formula.")
        self.index += 1
        return token

    def _match(self, kind: str) -> bool:
        token = self._peek()
        if token and token.kind == kind:
            self.index += 1
            return True
        return False
