import base64
from datetime import UTC, datetime
from typing import Any

from app.connectors.base import MockConnector

FIXTURE_TIME = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

# All values are synthetic/reserved. These objects are static and never make network calls.
CATALOG: dict[str, list[dict[str, Any]]] = {
    "wazuh": [
        {
            "id": "wazuh-auth-001",
            "kind": "authentication_failure",
            "severity": "high",
            "message": "Synthetic repeated authentication failures",
            "hostname": "srv-a.example.test",
            "ip": "192.0.2.10",
            "username": "demo-user",
        },
        {
            "id": "wazuh-auth-002",
            "kind": "authentication_failure",
            "severity": "high",
            "message": "Synthetic authentication failure",
            "hostname": "srv-a.example.test",
            "ip": "192.0.2.10",
            "username": "demo-user",
        },
    ],
    "rspamd": [
        {
            "id": "rspamd-mail-001",
            "kind": "phishing_message",
            "severity": "medium",
            "message": "Synthetic phishing classification",
            "hostname": "mail.example.test",
            "ip": "198.51.100.20",
            "username": "sender@example.test",
        },
        {
            "id": "rspamd-mail-002",
            "kind": "spam_message",
            "severity": "low",
            "message": "Synthetic spam classification",
            "hostname": "mail.example.test",
            "ip": "198.51.100.20",
            "username": "sender@example.test",
        },
    ],
    "clamav": [
        {
            "id": "clamav-scan-001",
            "kind": "malware_detected",
            "severity": "critical",
            "message": "Synthetic test signature detected (EICAR label only)",
            "hostname": "ws-a.example.test",
            "ip": "203.0.113.15",
            "username": "demo-user",
        },
        {
            "id": "clamav-scan-002",
            "kind": "file_clean",
            "severity": "info",
            "message": "Synthetic clean scan result",
            "hostname": "ws-a.example.test",
            "ip": "203.0.113.15",
            "username": "demo-user",
        },
    ],
    "misp": [
        {
            "id": "misp-ioc-001",
            "kind": "threat_indicator",
            "severity": "low",
            "message": "Synthetic IP indicator; not an enforcement verdict",
            "hostname": "intel.example.test",
            "ip": "192.0.2.200",
            "username": "feed-demo",
            "indicators": [
                {"type": "ip", "value": "192.0.2.200", "confidence": 50},
                {"type": "domain", "value": "indicator.example.test", "confidence": 50},
                {"type": "hash", "value": "0" * 64, "confidence": 50},
            ],
        },
    ],
}

RESOURCE_FOR_PROVIDER = {"wazuh": "alerts", "rspamd": "messages", "clamav": "scans", "misp": "iocs"}


class FixtureConnector(MockConnector):
    def __init__(self, provider: str):
        self.provider = provider

    def health_check(self) -> dict[str, Any]:
        return {"provider": self.provider, "status": "healthy", "is_simulated": True}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        try:
            start = (
                int(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode())
                if cursor
                else 0
            )
            if start < 0:
                raise ValueError()
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid fixture cursor") from exc
        page = CATALOG[self.provider][start : start + limit]
        next_cursor = (
            base64.urlsafe_b64encode(str(start + len(page)).encode()).decode().rstrip("=")
            if start + len(page) < len(CATALOG[self.provider])
            else None
        )
        return {"items": page, "next_cursor": next_cursor, "is_simulated": True}

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": self.provider,
            "external_event_id": raw_event["id"],
            "event_type": raw_event["kind"],
            "occurred_at": FIXTURE_TIME,
            "observed_at": FIXTURE_TIME,
            "severity": raw_event["severity"],
            "asset": {"hostname": raw_event["hostname"], "ip_address": raw_event["ip"]},
            "actor": {"username": raw_event["username"]},
            "message": raw_event["message"],
            "indicators": raw_event.get("indicators", []),
            "raw_event": raw_event,
            "schema_version": "1.0",
            "is_simulated": True,
        }

    def validate(self, event: dict[str, Any]) -> None:
        # Check connector-produced DTO fields without trusting arbitrary fixture data.
        if event.get("source") != self.provider or event.get("is_simulated") is not True:
            raise ValueError("invalid simulated source")


CONNECTORS = {name: FixtureConnector(name) for name in CATALOG}
