from enum import Enum

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionState(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
