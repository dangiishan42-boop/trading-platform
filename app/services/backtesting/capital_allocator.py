class CapitalAllocator:
    def allocate(self, capital: float, risk_fraction: float = 1.0) -> float:
        return capital * risk_fraction
