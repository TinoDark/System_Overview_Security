import re
from typing import Any

from app.connectors.base import Connector, ConnectorError
from app.connectors.parsing import parse_utc

LINE = re.compile(
    r"^(?P<timestamp>\S+)\t(?P<host>[^\t]*)\t(?P<path>[^\t]+)\t(?P<status>FOUND|OK)\t(?P<threat>.*)$"
)


class ClamavConnector(Connector):
    provider = "clamav"

    def __init__(self, configuration: dict[str, Any]):
        self.path = str(configuration["path"])

    def health_check(self) -> dict[str, Any]:
        try:
            with open(self.path, "rb"):
                pass
        except OSError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "ClamAV result log is not readable") from exc
        return {"provider": self.provider, "status": "healthy", "is_simulated": False}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        try:
            offset = int(cursor or 0)
        except ValueError as exc:
            raise ConnectorError("INVALID_CURSOR", "ClamAV cursor is invalid") from exc
        items: list[dict[str, Any]] = []
        try:
            with open(self.path, "rb") as handle:
                if offset > handle.seek(0, 2):
                    offset = 0
                handle.seek(offset)
                while len(items) < limit:
                    line = handle.readline()
                    if not line:
                        break
                    offset = handle.tell()
                    parsed = LINE.match(line.decode("utf-8", errors="replace").rstrip("\r\n"))
                    if parsed:
                        items.append(parsed.groupdict())
        except OSError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "ClamAV result log is not readable") from exc
        return {"items": items, "next_cursor": str(offset), "is_simulated": False}

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        occurred = parse_utc(raw_event["timestamp"])
        found = raw_event["status"] == "FOUND"
        threat = raw_event.get("threat") or ""
        identity = f"{raw_event['timestamp']}:{raw_event['path']}:{raw_event['status']}"
        return {
            "source": self.provider,
            "external_event_id": identity[:200],
            "event_type": "malware_detected" if found else "file_clean",
            "occurred_at": occurred,
            "observed_at": occurred,
            "severity": "critical" if found else "info",
            "asset": {"hostname": raw_event.get("host") or None, "ip_address": None},
            "actor": None,
            "message": (f"{threat} detected" if found else "Scan result clean")[:2000],
            "indicators": [],
            "raw_event": {
                "path": raw_event["path"],
                "status": raw_event["status"],
                "threat": threat,
            },
            "schema_version": "1.0",
            "is_simulated": False,
        }

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("source") != self.provider or event.get("is_simulated") is not False:
            raise ValueError("invalid clamav event")
