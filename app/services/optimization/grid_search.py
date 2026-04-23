class GridSearch:
    def run(self, parameter_grid: dict) -> list[dict]:
        return [{"parameters": parameter_grid, "score": 0.0}]
