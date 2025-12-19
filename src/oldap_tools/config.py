# src/oldap_tools/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AppConfig:
    graphdb_base: str
    repo: str
    user: Optional[str] = None
    password: Optional[str] = None