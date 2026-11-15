from typing import Any

import httpx

from app.connectors.base import Connector, ConnectorError
from app.connectors.config import read_env
from app.connectors.parsing import parse_utc

IP_TYPES = {"ip-src", "ip-dst", "ip-src|port", "ip-dst|port", "ip"}
DOMAIN_TYPES = {"domain", "hostname", "domain|ip"}
HASH_TYPES = {"md5", "sha1", "sha256", "sha512"}
THREAT = {"1": "high", "2": "medium", "3": "low", "4": "info"}


class MispConnector(Connector):
    """Pull published events. An indicator is context, not an enforcement verdict."""

    provider = "misp"

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

    def _search(self, limit: int, cursor: str | None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"returnFormat": "json", "limit": limit, "published": 1}
        if cursor:
            body["timestamp"] = cursor
        if self.configuration.get("filter"):
            body["tags"] = [str(self.configuration["filter"])]
        try:
            with self._client() as client:
                response = client.post(
                    f"{self.endpoint}/events/restSearch",
                    json=body,
                    headers={
                        "Authorization": read_env(str(self.configuration["secret_env"])),
                        "Accept": "application/json",
                    },
                )
        except httpx.HTTPError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "MISP API is unreachable") from exc
        if response.status_code >= 400:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "MISP search failed")
        payload = response.json().get("response") or []
        return [item.get("Event") or item for item in payload if isinstance(item, dict)]

    def health_check(self) -> dict[str, Any]:
        self._search(1, None)
        return {"provider": self.provider, "status": "healthy", "is_simulated": False}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        items = self._search(limit, cursor or since)
        stamps = [str(item.get("timestamp")) for item in items if item.get("timestamp")]
        return {
            "items": items,
            "next_cursor": max(stamps) if stamps else cursor,
            "is_simulated": False,
        }

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        occurred = parse_utc(raw_event.get("timestamp") or 0)
        indicators = []
        for attribute in raw_event.get("Attribute") or []:
            kind = str(attribute.get("type") or "")
            value = str(attribute.get("value") or "").split("|", 1)[0]
            mapped = None
            if kind in IP_TYPES:
                mapped = "ip"
            elif kind in DOMAIN_TYPES:
                mapped = "domain"
            elif kind in HASH_TYPES:
                mapped = "hash"
            if mapped and value:
                indicators.append({"type": mapped, "value": value})
        level = THREAT.get(str(raw_event.get("threat_level_id") or "4"), "info")
        return {
            "source": self.provider,
            "external_event_id": str(raw_event.get("id") or raw_event.get("uuid")),
            "event_type": "threat_indicator",
            "occurred_at": occurred,
            "observed_at": occurred,
            "severity": level,
            "asset": {"hostname": None, "ip_address": None},
            "actor": None,
            "message": "MISP indicator context; not an enforcement verdict",
            "indicators": indicators,
            "raw_event": {
                "id": raw_event.get("id"),
                "info": raw_event.get("info"),
                "threat_level_id": raw_event.get("threat_level_id"),
                "attribute_count": len(raw_event.get("Attribute") or []),
            },
            "schema_version": "1.0",
            "is_simulated": False,
        }

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("source") != self.provider or event.get("is_simulated") is not False:
            raise ValueError("invalid misp event")
        if "enforcement" in str(event.get("message")) and "not an enforcement" not in str(
            event.get("message")
        ):
            raise ValueError("misp event must not be an enforcement verdict")
