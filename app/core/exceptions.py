class TradingPlatformError(Exception):
    """Base app exception."""

class DataValidationError(TradingPlatformError):
    """Raised when market data is invalid."""

class InvalidRequestError(TradingPlatformError):
    """Raised when request input is invalid for the current operation."""

class ResourceConflictError(TradingPlatformError):
    """Raised when a create/update request conflicts with existing state."""

class StrategyNotFoundError(TradingPlatformError):
    """Raised when a requested strategy is not registered."""
