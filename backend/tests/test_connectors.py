import json

import httpx

from app.connectors.clamav import ClamavConnector
from app.connectors.misp import MispConnector
from app.connectors.rspamd import RspamdConnector
from app.connectors.suricata import SuricataConnector
from app.connectors.wazuh import WazuhConnector
from tests.conftest import login

WAZUH_ALERT = {
    "id": "1604",
    "timestamp": "2026-11-05T10:15:30.000+0000",
    "rule": {"level": 10, "description": "Multiple authentication failures"},
    "agent": {"name": "server-01", "ip": "192.0.2.10"},
    "data": {"srcuser": "unknown"},
}


def test_wazuh_normalizes_recorded_alert_without_network(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/security/authenticate"):
            assert request.headers["authorization"].startswith("Basic ")
            return httpx.Response(200, json={"data": {"token": "recorded-token"}})
        assert request.headers["authorization"] == "Bearer recorded-token"
        return httpx.Response(200, json={"data": {"affected_items": [WAZUH_ALERT]}})

    monkeypatch.setenv("WAZUH_API_USER", "svc")
    monkeypatch.setenv("WAZUH_API_PASSWORD", "not-in-the-event")
    connector = WazuhConnector(
        {
            "endpoint": "https://wazuh.example:55000",
            "username_env": "WAZUH_API_USER",
            "secret_env": "WAZUH_API_PASSWORD",
        },
        transport=httpx.MockTransport(handler),
    )
    batch = connector.collect(limit=10)
    normalized = connector.normalize(batch["items"][0])
    connector.validate(normalized)
    assert normalized["event_type"] == "authentication_failure"
    assert normalized["severity"] == "medium"
    assert normalized["is_simulated"] is False
    assert normalized["asset"]["hostname"] == "server-01"
    assert batch["next_cursor"] == WAZUH_ALERT["timestamp"]
    assert "not-in-the-event" not in json.dumps(normalized["raw_event"])


def test_suricata_rspamd_clamav_and_misp_recorded_payloads(tmp_path, monkeypatch):
    eve = tmp_path / "eve.json"
    eve.write_text(
        json.dumps(
            {
                "timestamp": "2026-11-05T10:15:30.000000+0000",
                "event_type": "alert",
                "flow_id": 7,
                "src_ip": "192.0.2.10",
                "host": "ids-01",
                "alert": {"signature": "ET TEST", "signature_id": 1, "severity": 1},
                "payload": "drop-me",
            }
        )
        + "\n"
    )
    suricata = SuricataConnector({"path": str(eve)})
    first = suricata.collect(limit=10)
    second = suricata.collect(cursor=first["next_cursor"], limit=10)
    assert len(first["items"]) == 1 and second["items"] == []
    suricata_event = suricata.normalize(first["items"][0])
    suricata.validate(suricata_event)
    assert suricata_event["severity"] == "critical"
    assert "payload" not in suricata_event["raw_event"]

    def rspamd(request: httpx.Request) -> httpx.Response:
        assert request.headers["password"] == "mailbox-secret"
        return httpx.Response(
            200,
            json=[
                {
                    "time": 1760000000,
                    "ip": "198.51.100.20",
                    "sender": "sender@example.test",
                    "action": "reject",
                    "score": 12.5,
                    "message-id": "<recorded@example.test>",
                }
            ],
        )

    monkeypatch.setenv("RSPAMD_PASSWORD", "mailbox-secret")
    rspamd_connector = RspamdConnector(
        {"endpoint": "http://rspamd.example:11334", "secret_env": "RSPAMD_PASSWORD"},
        transport=httpx.MockTransport(rspamd),
    )
    rspamd_event = rspamd_connector.normalize(rspamd_connector.collect(limit=5)["items"][0])
    rspamd_connector.validate(rspamd_event)
    assert rspamd_event["severity"] == "high"
    assert rspamd_event["is_simulated"] is False

    log = tmp_path / "clamav.log"
    log.write_text("2026-11-05T10:15:30Z\tws-01\t/tmp/sample\tFOUND\tEicar-Test-Signature\n")
    clamav = ClamavConnector({"path": str(log)})
    clamav_event = clamav.normalize(clamav.collect(limit=5)["items"][0])
    clamav.validate(clamav_event)
    assert clamav_event["event_type"] == "malware_detected"
    assert clamav_event["raw_event"]["path"] == "/tmp/sample"

    def misp(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "automation-key"
        return httpx.Response(
            200,
            json={
                "response": [
                    {
                        "Event": {
                            "id": "42",
                            "info": "recorded event",
                            "timestamp": "1760000000",
                            "threat_level_id": "2",
                            "Attribute": [
                                {"type": "ip-dst", "value": "192.0.2.200"},
                                {"type": "domain", "value": "indicator.example.test"},
                            ],
                        }
                    }
                ]
            },
        )

    monkeypatch.setenv("MISP_API_KEY", "automation-key")
    misp_connector = MispConnector(
        {"endpoint": "https://misp.example", "secret_env": "MISP_API_KEY"},
        transport=httpx.MockTransport(misp),
    )
    misp_event = misp_connector.normalize(misp_connector.collect(limit=5)["items"][0])
    misp_connector.validate(misp_event)
    assert misp_event["message"] == "MISP indicator context; not an enforcement verdict"
    assert misp_event["severity"] == "medium"
    assert {item["type"] for item in misp_event["indicators"]} == {"ip", "domain"}


def test_real_connector_configuration_and_isolated_collection(client, tmp_path, monkeypatch):
    admin, _ = login(client, "admin-a")
    analyst, _ = login(client, "analyst-a")
    missing = client.post(
        "/api/v1/integrations",
        headers=admin,
        json={"name": "Wazuh", "integration_type": "wazuh", "configuration": {}},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "CONNECTOR_NOT_CONFIGURED"

    leaked = client.post(
        "/api/v1/integrations",
        headers=admin,
        json={
            "name": "Wazuh",
            "integration_type": "wazuh",
            "configuration": {
                "endpoint": "https://wazuh.example:55000",
                "username_env": "WAZUH_API_USER",
                "secret_env": "WAZUH_API_PASSWORD",
                "password": "do-not-store",
            },
        },
    )
    assert leaked.status_code == 422

    monkeypatch.setenv("WAZUH_API_USER", "svc")
    monkeypatch.setenv("WAZUH_API_PASSWORD", "super-secret-value")
    created = client.post(
        "/api/v1/integrations",
        headers=admin,
        json={
            "name": "Wazuh lab",
            "integration_type": "wazuh",
            "configuration": {
                "endpoint": "https://wazuh.example:55000",
                "username_env": "WAZUH_API_USER",
                "secret_env": "WAZUH_API_PASSWORD",
            },
        },
    )
    assert created.status_code == 201
    visible = json.dumps(created.json()["data"])
    assert "super-secret-value" not in visible
    assert created.json()["data"]["configuration"]["secret_env"] == "WAZUH_API_PASSWORD"
    assert created.json()["data"]["is_simulated"] is False

    log = tmp_path / "clamav.log"
    log.write_text("2026-11-05T10:15:30Z\tws-01\t/tmp/sample\tOK\t\n")
    clamav = client.post(
        "/api/v1/integrations",
        headers=admin,
        json={
            "name": "ClamAV log",
            "integration_type": "clamav",
            "configuration": {"path": str(log)},
        },
    )
    assert clamav.status_code == 201
    integration_id = clamav.json()["data"]["id"]
    first = client.post(f"/api/v1/integrations/{integration_id}/collect", headers=analyst)
    assert first.status_code == 200
    assert first.json()["data"]["received"] == 1
    assert first.json()["data"]["is_simulated"] is False
    second = client.post(f"/api/v1/integrations/{integration_id}/collect", headers=analyst)
    assert second.json()["data"]["received"] == 0

    missing_log = client.post(
        "/api/v1/integrations",
        headers=admin,
        json={
            "name": "Missing log",
            "integration_type": "suricata",
            "configuration": {"path": str(tmp_path / "missing.json")},
        },
    )
    assert missing_log.status_code == 201
    failed = client.post(
        f"/api/v1/integrations/{missing_log.json()['data']['id']}/test", headers=analyst
    )
    assert failed.status_code == 503
    mocks = client.get("/api/v1/integrations", headers=analyst).json()["data"]
    wazuh = next(item for item in mocks if item["integration_type"] == "mock_wazuh")
    assert (
        client.post(f"/api/v1/integrations/{wazuh['id']}/collect", headers=analyst).status_code
        == 200
    )
