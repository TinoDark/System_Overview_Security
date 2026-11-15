from typing import Any

import httpx

from app.connectors.base import Connector, ConnectorError
from app.connectors.config import read_env
from app.connectors.parsing import bounded_raw, parse_utc, wazuh_severity


class WazuhConnector(Connector):
    provider = "wazuh"

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

    def _token(self, client: httpx.Client) -> str:
        try:
            response = client.post(
                f"{self.endpoint}/security/authenticate",
                auth=(
                    read_env(str(self.configuration["username_env"])),
                    read_env(str(self.configuration["secret_env"])),
                ),
            )
        except httpx.HTTPError as exc:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Wazuh API is unreachable") from exc
        if response.status_code >= 400:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Wazuh authentication failed")
        token = response.json().get("data", {}).get("token")
        if not token:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Wazuh authentication failed")
        return str(token)

    def health_check(self) -> dict[str, Any]:
        with self._client() as client:
            self._token(client)
        return {"provider": self.provider, "status": "healthy", "is_simulated": False}

    def collect(
        self, cursor: str | None = None, since: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "sort": "+timestamp"}
        mark = cursor or since
        if mark:
            params["q"] = f"timestamp>{mark}"
        with self._client() as client:
            token = self._token(client)
            try:
                response = client.get(
                    f"{self.endpoint}/alerts",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except httpx.HTTPError as exc:
                raise ConnectorError("CONNECTOR_UNAVAILABLE", "Wazuh API is unreachable") from exc
        if response.status_code >= 400:
            raise ConnectorError("CONNECTOR_UNAVAILABLE", "Wazuh alert collection failed")
        items = response.json().get("data", {}).get("affected_items") or []
        stamps = [item.get("timestamp") for item in items if item.get("timestamp")]
        return {
            "items": items,
            "next_cursor": max(stamps) if stamps else cursor,
            "is_simulated": False,
        }

    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        rule = raw_event.get("rule") or {}
        agent = raw_event.get("agent") or {}
        data = raw_event.get("data") or {}
        occurred = parse_utc(raw_event["timestamp"])
        level = int(rule.get("level") or 0)
        description = str(rule.get("description") or "Wazuh alert")
        event_type = "alert"
        if "authentication" in description.lower():
            event_type = "authentication_failure"
        return {
            "source": self.provider,
            "external_event_id": str(raw_event.get("id") or raw_event["timestamp"]),
            "event_type": event_type,
            "occurred_at": occurred,
            "observed_at": occurred,
            "severity": wazuh_severity(level),
            "asset": {"hostname": agent.get("name"), "ip_address": agent.get("ip")},
            "actor": {"username": data.get("srcuser") or data.get("dstuser")},
            "message": description[:2000],
            "indicators": [],
            "raw_event": bounded_raw(raw_event, ("full_log",)),
            "schema_version": "1.0",
            "is_simulated": False,
        }

    def validate(self, event: dict[str, Any]) -> None:
        if event.get("source") != self.provider or event.get("is_simulated") is not False:
            raise ValueError("invalid wazuh event")
