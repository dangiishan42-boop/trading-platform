import json

class JsonService:
    def dumps(self, payload: dict) -> str:
        return json.dumps(payload, indent=2)

    def loads(self, payload: str) -> dict:
        return json.loads(payload)
