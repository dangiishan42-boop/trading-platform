from datetime import datetime

def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)
