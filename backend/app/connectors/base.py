from abc import ABC, abstractmethod
from typing import Any


class ConnectorError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class Connector(ABC):
    provider: str
    simulated: bool = False

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...

    @abstractmethod
    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]: ...

    @abstractmethod
    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def validate(self, event: dict[str, Any]) -> None: ...


class MockConnector(Connector):
    simulated = True
