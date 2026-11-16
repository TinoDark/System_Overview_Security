import os
import re
from typing import Any
from urllib.parse import urlparse

from app.connectors.base import ConnectorError

ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
FORBIDDEN_KEYS = {"password", "token", "api_key", "secret", "authorization", "passwd"}
PUBLIC_KEYS = {
    "endpoint",
    "path",
    "secret_env",
    "username_env",
    "ca_file",
    "cursor",
    "verify_tls",
    "filter",
}
REQUIRED = {
    "wazuh": ("endpoint", "username_env", "secret_env"),
    "suricata": ("path",),
    "rspamd": ("endpoint", "secret_env"),
    "clamav": ("path",),
    "misp": ("endpoint", "secret_env"),
}
REAL_TYPES = frozenset(REQUIRED)


def public_configuration(configuration: dict[str, Any] | None) -> dict[str, Any]:
    return {key: value for key, value in (configuration or {}).items() if key in PUBLIC_KEYS}


def _env_name(configuration: dict[str, Any], key: str) -> str:
    value = configuration.get(key)
    if not isinstance(value, str) or not ENV_NAME.fullmatch(value):
        raise ConnectorError(
            "CONNECTOR_NOT_CONFIGURED",
            f"{key} must be the name of an environment variable",
        )
    return value


def read_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise ConnectorError(
            "CONNECTOR_NOT_CONFIGURED",
            f"Environment variable {name} is not set",
        )
    return value


def validate_connector_config(provider: str, configuration: dict[str, Any] | None) -> dict[str, Any]:
    configuration = configuration or {}
    if provider not in REQUIRED:
        raise ConnectorError("UNSUPPORTED_CONNECTOR", "Connector is not supported")
    unknown = set(configuration) - PUBLIC_KEYS
    leaked = unknown & FORBIDDEN_KEYS or FORBIDDEN_KEYS & set(configuration)
    if leaked or unknown:
        raise ConnectorError(
            "INVALID_CONFIGURATION",
            "Configuration accepts only access references, not secret values",
        )
    missing = [key for key in REQUIRED[provider] if not configuration.get(key)]
    if missing:
        raise ConnectorError(
            "CONNECTOR_NOT_CONFIGURED",
            "Missing access reference: " + ", ".join(missing),
        )
    if "endpoint" in REQUIRED[provider]:
        parsed = urlparse(str(configuration["endpoint"]))
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
            raise ConnectorError(
                "INVALID_CONFIGURATION",
                "endpoint must be an http(s) URL without embedded credentials",
            )
    if "path" in REQUIRED[provider]:
        path = str(configuration["path"])
        if not path.startswith("/") or "\n" in path or "\x00" in path:
            raise ConnectorError("INVALID_CONFIGURATION", "path must be an absolute file path")
    for key in ("secret_env", "username_env"):
        if key in REQUIRED[provider]:
            read_env(_env_name(configuration, key))
    return configuration
