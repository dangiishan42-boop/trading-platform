class ReportService:
    def generate(self, metrics: dict, trades: list[dict]) -> dict:
        return {"metrics": metrics, "trades": trades}
