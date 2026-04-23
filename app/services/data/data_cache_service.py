class DataCacheService:
    def __init__(self):
        self._cache: dict[str, object] = {}

    def get(self, key: str):
        return self._cache.get(key)

    def set(self, key: str, value) -> None:
        self._cache[key] = value
