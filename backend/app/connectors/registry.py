from typing import Any

import httpx

from app.connectors.base import Connector, ConnectorError
from app.connectors.clamav import ClamavConnector
from app.connectors.config import REAL_TYPES, validate_connector_config
from app.connectors.fixtures import CONNECTORS
from app.connectors.misp import MispConnector
from app.connectors.rspamd import RspamdConnector
from app.connectors.suricata import SuricataConnector
from app.connectors.wazuh import WazuhConnector

SOURCES = frozenset({*CONNECTORS, *REAL_TYPES})


def build_connector(
    integration_type: str,
    configuration: dict[str, Any] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Connector:
    if integration_type.startswith("mock_"):
        provider = integration_type.removeprefix("mock_")
        connector = CONNECTORS.get(provider)
        if connector is None:
            raise ConnectorError("UNSUPPORTED_CONNECTOR", "Only known connectors are supported")
        return connector
    if integration_type not in REAL_TYPES:
        raise ConnectorError("UNSUPPORTED_CONNECTOR", "Only known connectors are supported")
    config = validate_connector_config(integration_type, configuration)
    if integration_type == "wazuh":
        return WazuhConnector(config, transport=transport)
    if integration_type == "suricata":
        return SuricataConnector(config)
    if integration_type == "rspamd":
        return RspamdConnector(config, transport=transport)
    if integration_type == "clamav":
        return ClamavConnector(config)
    return MispConnector(config, transport=transport)
