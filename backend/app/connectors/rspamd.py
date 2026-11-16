from typing import Any

import httpx

from app.connectors.base import Connector, ConnectorError
from app.connectors.config import read_env
from app.connectors.parsing import parse_utc


class RspamdConnector(Connector):
    provider = "rspamd"

    def __init__(self, configuration: dict[str, Any], transport: httpx.BaseTransport | None = None):
        self.configuration = configuration
        self.transport = transport
        self.endpoint = str(configuration["endpoint"]).rstrip("/")

    def _client(self) -> httpx.Client:
        verify: bool | str = True
        if self.configuration.get("verify_tls") is False:
            verify = False
        elif self.configuration.get("ca_file"):
            verify = str(self.configuration["ca_file"])
        return httpx.Client(transport=self.transport, timeout=10.0, verify=verify)

    def _history(self, limit: int) -> list[dict[str, Any]]:
        try:
            with self._client() as client:
                response = client.get(
                    f"{self.endpoint}/history",
                    params={"limit": limit},
                    headers={"Password": read_env(str(self.configuration["secret_env"]))},
                )
        except httpx.HTTPError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Rspamd controller is unreachable") from exc
        if response.status_code >= 400:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Rspamd history request failed")
        payload = response.json()
        rows = payload.get("rows") if isinstance(payload, dict) else payload
        return [row for row in rows or [] if isinstance(row, dict)]

    def health_check(self) -> dict[str, Any]:
        self._history(1)
        return {"provider": self.provider, "status": "healthy", "is_simulated": False}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        mark = float(cursor or since or 0)
        rows = [row for row in self._history(limit) if float(row.get("time") or 0) > mark]
        latest = max((float(row.get("time") or 0) for row in rows), default=mark)
        return {
            "items": rows,
            "next_cursor": str(latest) if rows else cursor,
            "is_simulated": False,
        }

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        occurred = parse_utc(raw_event["time"])
        action = str(raw_event.get("action") or "no action")
        score = float(raw_event.get("score") or 0)
        if action == "reject" or score >= 10:
            severity = "high"
        elif score >= 5:
            severity = "medium"
        elif score > 0:
            severity = "low"
        else:
            severity = "info"
        identity = str(raw_event.get("message-id") or f"{raw_event['time']}:{raw_event.get('ip', '')}")
        return {
            "source": self.provider,
            "external_event_id": identity[:200],
            "event_type": "spam_message" if action != "no action" else "mail_scored",
            "occurred_at": occurred,
            "observed_at": occurred,
            "severity": severity,
            "asset": {"hostname": None, "ip_address": raw_event.get("ip")},
            "actor": {"username": raw_event.get("sender")},
            "message": f"Rspamd {action}, score {score}"[:2000],
            "indicators": [],
            "raw_event": {
                "action": action,
                "score": score,
                "subject": raw_event.get("subject"),
            },
            "schema_version": "1.0",
            "is_simulated": False,
        }

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("source") != self.provider or event.get("is_simulated") is not False:
            raise ValueError("invalid rspamd event")
