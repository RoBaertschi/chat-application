from typing import Any
from rich.console import Console


console = Console()


class User:
  username: str
  jwt: Any

  def __init__(self, username, jwt) -> None:
    self.username = username
    self.jwt = jwt
