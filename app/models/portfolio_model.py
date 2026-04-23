from dataclasses import dataclass

@dataclass
class PortfolioSnapshot:
    timestamp: str
    equity: float
    cash: float
    position_qty: int
