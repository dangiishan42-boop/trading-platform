class AuthService:
    def login(self, username: str, password: str) -> dict:
        return {"username": username, "token": "demo-token"}
