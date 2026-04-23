def pct_change(a: float, b: float) -> float:
    return ((b - a) / a) * 100 if a else 0.0
