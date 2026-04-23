from dataclasses import dataclass

@dataclass
class UserProfile:
    username: str
    role: str = "admin"
