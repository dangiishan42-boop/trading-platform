class CustomStrategyParser:
    def parse(self, payload: dict) -> dict:
        return {
            "name": payload.get("strategy_name", "custom"),
            "entry_rule": payload.get("entry_rule", ""),
            "exit_rule": payload.get("exit_rule", ""),
            "parameters": payload.get("parameters", {}),
        }
