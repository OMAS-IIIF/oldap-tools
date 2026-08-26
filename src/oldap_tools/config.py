# src/oldap_tools/config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    graphdb_base: str
    repo: str
    api_base: str = "http://localhost:8000"
    media_base: str = "http://localhost:8088"
    user: str | None = None
    password: str | None = None
    graphdb_user: str | None = None
    graphdb_password: str | None = None
