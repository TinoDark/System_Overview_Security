import json
from typing import Any

from app.connectors.base import Connector, ConnectorError
from app.connectors.parsing import bounded_raw, parse_utc, suricata_severity


class SuricataConnector(Connector):
    provider = "suricata"

    def __init__(self, configuration: dict[str, Any]):
        self.path = str(configuration["path"])

    def health_check(self) -> dict[str, Any]:
        try:
            with open(self.path, "rb"):
                pass
        except OSError as exc:
            raise ConnectorError(
                "CONNECTOR_UNAVAILABLE", "Suricata EVE file is not readable"
            ) from exc
        return {"provider": self.provider, "status": "healthy", "is_simulated": False}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        try:
            offset = int(cursor or 0)
        except ValueError as exc:
            raise ConnectorError("INVALID_CURSOR", "Suricata cursor is invalid") from exc
        if offset < 0:
            raise ConnectorError("INVALID_CURSOR", "Suricata cursor is invalid")
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
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(record, dict) and record.get("event_type"):
                        items.append(record)
        except OSError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Suricata EVE file is not readable") from exc
        return {"items": items, "next_cursor": str(offset), "is_simulated": False}

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        occurred = parse_utc(raw_event["timestamp"])
        alert = raw_event.get("alert") or {}
        signature_id = alert.get("signature_id", "")
        identity = f"{raw_event.get('flow_id', '')}:{raw_event['timestamp']}:{signature_id}"
        level = int(alert.get("severity") or 4)
        message = str(alert.get("signature") or raw_event.get("event_type"))
        return {
            "source": self.provider,
            "external_event_id": identity[:200],
            "event_type": str(raw_event.get("event_type") or "alert")[:100],
            "occurred_at": occurred,
            "observed_at": occurred,
            "severity": suricata_severity(level) if alert else "info",
            "asset": {
                "hostname": raw_event.get("host"),
                "ip_address": raw_event.get("src_ip") or raw_event.get("dest_ip"),
            },
            "actor": None,
            "message": message[:2000],
            "indicators": [],
            "raw_event": bounded_raw(raw_event, ("payload", "payload_printable", "packet")),
            "schema_version": "1.0",
            "is_simulated": False,
        }

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("source") != self.provider or event.get("is_simulated") is not False:
            raise ValueError("invalid suricata event")
