class CacheService:
    def __init__(self):
        self._memory = {}

    def get(self, key):
        return self._memory.get(key)

    def set(self, key, value):
        self._memory[key] = value
