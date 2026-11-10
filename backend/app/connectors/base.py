from abc import ABC, abstractmethod
from typing import Any


class MockConnector(ABC):
    provider: str

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
