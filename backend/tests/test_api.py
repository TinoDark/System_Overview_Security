from uuid import UUID

from app.db.models import Approval

ORG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ASSET_B = "b0000000-0000-4000-8000-000000000099"


def test_auth_required_and_invalid_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_TOKEN"


def test_frontend_cors_allows_local_api_headers(client):
    preflight = client.options(
        "/api/v1/auth/mock-login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-organization-id",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"

    denied = client.options(
        "/api/v1/auth/mock-login",
        headers={
            "Origin": "http://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_mock_logout_invalidates_opaque_token(client):
    from tests.conftest import login

    headers, _ = login(client)
    assert client.post("/api/v1/auth/mock-logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_role_based_access_and_login_catalog(client):
    from tests.conftest import login

    headers, _ = login(client, "observer-a")
    denied = client.post(
        "/api/v1/assets", headers=headers, json={"name": "x", "asset_type": "server"}
    )
    assert denied.status_code == 403
    assert client.get("/api/v1/dashboard/summary", headers=headers).status_code == 200
    timeline = client.get("/api/v1/dashboard/timeline", headers=headers)
    assert timeline.status_code == 200
    assert timeline.json()["data"] == []
    for path in (
        "/api/v1/incidents",
        "/api/v1/events",
        "/api/v1/assets",
        "/api/v1/integrations",
        "/api/v1/policies",
        "/api/v1/approvals",
        "/api/v1/audit-logs",
    ):
        assert client.get(path, headers=headers).status_code == 403

    operator, _ = login(client, "operator-a")
    assert client.get("/api/v1/incidents", headers=operator).status_code == 200
    assert client.get("/api/v1/events", headers=operator).status_code == 403
    assert client.get("/api/v1/audit-logs", headers=operator).status_code == 403

    auditor, _ = login(client, "auditor-a")
    assert client.get("/api/v1/audit-logs", headers=auditor).status_code == 200
    assert client.get("/api/v1/incidents", headers=auditor).status_code == 403

    analyst, _ = login(client, "analyst-a")
    assert client.get("/api/v1/events", headers=analyst).status_code == 200
    assert client.get("/api/v1/audit-logs", headers=analyst).status_code == 403


def test_tenant_header_membership_and_known_uuid_isolation(client):
    from tests.conftest import login

    headers, _ = login(client, "analyst-a")
    assert client.get(f"/api/v1/assets/{ASSET_B}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/organizations/{ORG_B}", headers=headers).status_code == 404
    assert (
        client.get("/api/v1/assets", headers={**headers, "X-Organization-ID": ORG_B}).status_code
        == 403
    )
    assert all(
        row["organization_id"] == ORG_A
        for row in client.get("/api/v1/assets", headers=headers).json()["data"]
    )


def test_ambiguous_tenant_selection_fails_closed(client):
    from tests.conftest import login

    headers, _ = login(client, "super-admin")
    without_selection = dict(headers)
    without_selection.pop("X-Organization-ID")
    assert client.get("/api/v1/assets", headers=without_selection).status_code == 400
    assert (
        client.get("/api/v1/assets", headers={**headers, "X-Organization-ID": ORG_B}).status_code
        == 200
    )


def test_known_tenant_b_event_incident_approval_and_response_are_hidden(client):
    from tests.conftest import login

    analyst_a, _ = login(client, "analyst-a")
    analyst_b, _ = login(client, "analyst-b")
    admin_b, _ = login(client, "admin-b")
    client.post(
        "/api/v1/policies",
        headers=admin_b,
        json={
            "name": "Tenant B fixture policy",
            "enabled": True,
            "trigger_min_severity": "high",
        },
    )
    integration_b = next(
        i
        for i in client.get("/api/v1/integrations", headers=analyst_b).json()["data"]
        if i["integration_type"] == "mock_wazuh"
    )
    client.post(f"/api/v1/integrations/{integration_b['id']}/collect", headers=analyst_b)
    incident_id_b = client.get("/api/v1/incidents", headers=analyst_b).json()["data"][0]["id"]
    incident_b = client.get(f"/api/v1/incidents/{incident_id_b}", headers=analyst_b).json()["data"]
    approval_b = client.get("/api/v1/approvals", headers=analyst_b).json()["data"][0]
    response_b = client.get(
        f"/api/v1/responses/{approval_b['response_id']}", headers=analyst_b
    ).json()["data"]
    event_b_id = incident_b["event_ids"][0]
    assert client.get(f"/api/v1/incidents/{incident_b['id']}", headers=analyst_a).status_code == 404
    assert client.get(f"/api/v1/events/{event_b_id}", headers=analyst_a).status_code == 404
    assert client.get(f"/api/v1/responses/{response_b['id']}", headers=analyst_a).status_code == 404
    assert (
        client.post(
            f"/api/v1/approvals/{approval_b['id']}/approve",
            headers=analyst_a,
            json={"justification": "Cross-tenant attempt"},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/audit-logs", headers=analyst_a).status_code == 403


def test_database_rejects_cross_tenant_incident_event_links(client):
    from sqlalchemy.exc import IntegrityError

    from app.db.models import IncidentEvent
    from tests.conftest import login

    analyst_a, org_a = login(client, "analyst-a")
    analyst_b, _ = login(client, "analyst-b")
    for headers in (analyst_a, analyst_b):
        integrations = client.get("/api/v1/integrations", headers=headers).json()["data"]
        wazuh = next(item for item in integrations if item["integration_type"] == "mock_wazuh")
        collected = client.post(
            f"/api/v1/integrations/{wazuh['id']}/collect", headers=headers
        )
        assert collected.status_code == 200

    incident_a = client.get("/api/v1/incidents", headers=analyst_a).json()["data"][0]
    event_b = client.get("/api/v1/events", headers=analyst_b).json()["data"][0]
    with client.app.state.test_session_factory() as db:
        db.add(
            IncidentEvent(
                organization_id=UUID(org_a),
                incident_id=UUID(incident_a["id"]),
                event_id=UUID(event_b["event_id"]),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Database accepted a cross-tenant incident/event link")


def test_mock_routes_are_synthetic_and_bounded(client):
    from tests.conftest import login

    headers, _ = login(client)
    payload = client.get("/api/v1/mock/wazuh/alerts?limit=1", headers=headers)
    assert payload.status_code == 200
    assert payload.json()["meta"]["is_simulated"] is True
    assert len(payload.json()["data"]) == 1
    assert payload.json()["meta"]["next_cursor"] == "MQ"
    assert client.get("/api/v1/mock/unknown/alerts", headers=headers).status_code == 404
    assert client.get("/api/v1/mock/clamav/health", headers=headers).json()["data"]["is_simulated"]
    assert client.get("/api/v1/mock/wazuh/alerts?limit=101", headers=headers).status_code == 422


def test_ingestion_is_persistent_idempotent_and_creates_explainable_incident(client):
    from tests.conftest import login

    headers, _ = login(client)
    integrations = client.get("/api/v1/integrations", headers=headers).json()["data"]
    wazuh = next(x for x in integrations if x["integration_type"] == "mock_wazuh")
    first = client.post(f"/api/v1/integrations/{wazuh['id']}/collect", headers=headers).json()[
        "data"
    ]
    second = client.post(f"/api/v1/integrations/{wazuh['id']}/collect", headers=headers).json()[
        "data"
    ]
    assert first["received"] == 2 and first["inserted"] == 2 and first["incidents_created"] == 1
    assert second["inserted"] == 0 and second["duplicates"] == 2
    incidents = client.get("/api/v1/incidents", headers=headers).json()["data"]
    assert len(incidents) == 1
    assert incidents[0]["risk_score"] >= 60
    assert incidents[0]["risk_factors"][0]["explanation"]
    comment = client.post(
        f"/api/v1/incidents/{incidents[0]['id']}/comments",
        headers=headers,
        json={"body": "Synthetic incident reviewed"},
    )
    assert comment.status_code == 201
    details = client.get(f"/api/v1/incidents/{incidents[0]['id']}", headers=headers).json()["data"]
    assert len(details["event_ids"]) == 2
    assert details["response_id"] is None
    assert details["approval"] is None
    assert details["comments"][0]["body"] == "Synthetic incident reviewed"
    timeline = client.get("/api/v1/dashboard/timeline", headers=headers).json()["data"]
    assert len(timeline) == 2
    summary = client.get("/api/v1/dashboard/summary", headers=headers).json()["data"]
    assert summary["events_24h"] == 2
    assert summary["active_integrations"] == 4
    assert summary["total_assets"] == 1


def test_approval_separation_expiry_and_kill_switch(client):
    from tests.conftest import login

    analyst, _ = login(client, "analyst-a")
    admin, _ = login(client, "admin-a")
    operator, _ = login(client, "operator-a")
    integration = next(
        i
        for i in client.get("/api/v1/integrations", headers=analyst).json()["data"]
        if i["integration_type"] == "mock_wazuh"
    )
    policy = client.post(
        "/api/v1/policies",
        headers=admin,
        json={
            "name": "Demo containment",
            "enabled": True,
            "trigger_min_severity": "high",
            "action_type": "simulate_containment",
        },
    )
    assert policy.status_code == 201
    client.post(f"/api/v1/integrations/{integration['id']}/collect", headers=analyst)
    approval = client.get("/api/v1/approvals", headers=analyst).json()["data"][0]
    response_id = approval["response_id"]
    incident = client.get(f"/api/v1/incidents/{approval['incident_id']}", headers=analyst).json()[
        "data"
    ]
    assert incident["response_id"] == response_id
    assert incident["approval"]["id"] == approval["id"]
    response_data = client.get(f"/api/v1/responses/{response_id}", headers=analyst).json()["data"]
    dry_run = client.post(f"/api/v1/responses/{response_id}/dry-run", headers=operator)
    assert dry_run.status_code == 200
    assert dry_run.json()["data"]["external_effect"] is False
    assert (
        client.get(f"/api/v1/responses/{response_id}", headers=analyst).json()["data"]["status"]
        == "proposed"
    )
    own_decision = client.post(
        f"/api/v1/approvals/{approval['id']}/approve",
        headers=analyst,
        json={"justification": "Independent review"},
    )
    assert own_decision.status_code == 403
    decided = client.post(
        f"/api/v1/approvals/{approval['id']}/approve",
        headers=admin,
        json={"justification": "Reviewed simulation request"},
    )
    assert decided.status_code == 200
    repeated_decision = client.post(
        f"/api/v1/approvals/{approval['id']}/reject",
        headers=admin,
        json={"justification": "Second decision"},
    )
    assert repeated_decision.status_code == 409
    response = client.post(
        f"/api/v1/responses/{response_id}/execute",
        headers={
            **operator,
            "Idempotency-Key": response_data["idempotency_key"],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESPONSES_DISABLED"
    client.app.state.config.responses_enabled = True
    executed = client.post(
        f"/api/v1/responses/{response_id}/execute",
        headers={
            **operator,
            "Idempotency-Key": response_data["idempotency_key"],
        },
    )
    assert executed.status_code == 200
    assert executed.json()["data"]["status"] == "simulated"
    assert executed.json()["data"]["result"]["verified"] is True
    assert (
        client.get("/api/v1/dashboard/summary", headers=analyst).json()["data"][
            "responses_simulated"
        ]
        == 1
    )


def test_schema_rejects_secret_or_real_connector_configuration(client):
    from tests.conftest import login

    headers, _ = login(client, "admin-a")
    result = client.post(
        "/api/v1/integrations",
        headers=headers,
        json={
            "name": "unsafe mock",
            "integration_type": "mock_wazuh",
            "configuration": {"endpoint": "reserved-test-value"},
        },
    )
    assert result.status_code == 422


def test_expired_approval_cannot_be_decided(client):
    from datetime import timedelta

    from app.db.models import utcnow
    from tests.conftest import login

    analyst, _ = login(client, "analyst-a")
    admin, _ = login(client, "admin-a")
    integrations = client.get("/api/v1/integrations", headers=analyst).json()["data"]
    wazuh = next(x for x in integrations if x["integration_type"] == "mock_wazuh")
    client.post(
        "/api/v1/policies",
        headers=admin,
        json={
            "name": "Expiring approval policy",
            "enabled": True,
            "trigger_min_severity": "high",
        },
    )
    client.post(f"/api/v1/integrations/{wazuh['id']}/collect", headers=analyst)
    approval = client.get("/api/v1/approvals", headers=analyst).json()["data"][0]
    with client.app.state.test_session_factory() as db:
        row = db.get(Approval, UUID(approval["id"]))
        row.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    result = client.post(
        f"/api/v1/approvals/{approval['id']}/approve",
        headers=admin,
        json={"justification": "Too late"},
    )
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "APPROVAL_EXPIRED"


def test_admin_creates_member_only_inside_administered_organizations(client):
    from tests.conftest import login

    analyst, _ = login(client, "analyst-a")
    assert client.get("/api/v1/members", headers=analyst).status_code == 403
    denied = client.post(
        "/api/v1/members",
        headers=analyst,
        json={
            "user_key": "new-analyst",
            "display_name": "New Analyst",
            "memberships": [{"organization_id": ORG_A, "role": "soc_analyst"}],
        },
    )
    assert denied.status_code == 403

    admin, _ = login(client, "admin-a")
    cross_tenant = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": "cross-tenant",
            "display_name": "Cross Tenant",
            "memberships": [{"organization_id": ORG_B, "role": "observer"}],
        },
    )
    assert cross_tenant.status_code == 403
    elevated = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": "elevated-admin",
            "display_name": "Elevated",
            "memberships": [{"organization_id": ORG_A, "role": "super_admin"}],
        },
    )
    assert elevated.status_code == 403

    created = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": "Nina.Analyst",
            "display_name": " Nina Analyst ",
            "memberships": [{"organization_id": ORG_A, "role": "soc_analyst"}],
        },
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["user_key"] == "nina.analyst"
    assert body["display_name"] == "Nina Analyst"
    assert body["memberships"] == [
        {
            "organization_id": ORG_A,
            "organization_name": "Demo Organization A",
            "role": "soc_analyst",
        }
    ]
    listed = client.get("/api/v1/members", headers=admin).json()["data"]
    assert any(row["user_id"] == body["user_id"] for row in listed)
    assert all(row["user_key"] != "super-admin" for row in listed)
    assert all(
        membership["role"] != "super_admin"
        for row in listed
        for membership in row["memberships"]
    )
    admin_b, _ = login(client, "admin-b")
    hidden = client.get("/api/v1/members", headers=admin_b).json()["data"]
    assert all(row["user_id"] != body["user_id"] for row in hidden)

    duplicate = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": body["user_key"],
            "display_name": "Again",
            "memberships": [{"organization_id": ORG_A, "role": "observer"}],
        },
    )
    assert duplicate.status_code == 409

    session = client.post("/api/v1/auth/mock-login", json={"user_key": body["user_key"]})
    assert session.status_code == 200
    assert session.json()["data"]["principal"]["memberships"][0]["organization_id"] == ORG_A


def test_super_admin_assigns_one_user_to_several_organizations(client):
    from tests.conftest import login

    headers, _ = login(client, "super-admin")
    created = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "user_key": "shared-operator",
            "display_name": "Shared Operator",
            "memberships": [
                {"organization_id": ORG_A, "role": "operator"},
                {"organization_id": ORG_B, "role": "auditor"},
            ],
        },
    )
    assert created.status_code == 201
    roles = {
        item["organization_id"]: item["role"] for item in created.json()["data"]["memberships"]
    }
    assert roles == {ORG_A: "operator", ORG_B: "auditor"}
    listed = client.get("/api/v1/members", headers=headers).json()["data"]
    row = next(item for item in listed if item["user_key"] == "shared-operator")
    assert {item["organization_id"] for item in row["memberships"]} == {ORG_A, ORG_B}
    platform = client.get("/api/v1/members", headers=headers).json()["data"]
    assert any(item["user_key"] == "super-admin" for item in platform)


def test_role_ladder_hides_super_admin_and_replaces_role_on_promotion(client):
    from tests.conftest import login

    admin, _ = login(client, "admin-a")
    created = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": "watcher",
            "display_name": "Watcher",
            "memberships": [{"organization_id": ORG_A, "role": "observer"}],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["data"]["user_id"]
    same_rank = client.post(
        "/api/v1/members",
        headers=admin,
        json={
            "user_key": "second-admin",
            "display_name": "Second Admin",
            "memberships": [{"organization_id": ORG_A, "role": "security_admin"}],
        },
    )
    assert same_rank.status_code == 201

    promoted = client.patch(
        f"/api/v1/members/{user_id}",
        headers=admin,
        json={"organization_id": ORG_A, "role": "operator"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["data"]["memberships"] == [
        {
            "organization_id": ORG_A,
            "organization_name": "Demo Organization A",
            "role": "operator",
        }
    ]
    above = client.patch(
        f"/api/v1/members/{user_id}",
        headers=admin,
        json={"organization_id": ORG_A, "role": "super_admin"},
    )
    assert above.status_code == 403
    hidden = client.patch(
        "/api/v1/members/90000000-0000-4000-8000-000000000001",
        headers=admin,
        json={"organization_id": ORG_A, "role": "observer"},
    )
    assert hidden.status_code == 404
    own = client.patch(
        "/api/v1/members/10000000-0000-4000-8000-000000000002",
        headers=admin,
        json={"organization_id": ORG_A, "role": "observer"},
    )
    assert own.status_code == 403

    super_headers, _ = login(client, "super-admin")
    peer = client.post(
        "/api/v1/members",
        headers=super_headers,
        json={
            "user_key": "peer-super",
            "display_name": "Peer Super",
            "memberships": [{"organization_id": ORG_A, "role": "super_admin"}],
        },
    )
    assert peer.status_code == 201
    visible_to_admin = client.get("/api/v1/members", headers=admin).json()["data"]
    assert all(row["user_key"] != "peer-super" for row in visible_to_admin)
    visible_to_super = client.get("/api/v1/members", headers=super_headers).json()["data"]
    assert any(row["user_key"] == "peer-super" for row in visible_to_super)
    locked = client.patch(
        f"/api/v1/members/{peer.json()['data']['user_id']}",
        headers=super_headers,
        json={"organization_id": ORG_A, "role": "operator"},
    )
    assert locked.status_code == 403


def test_super_admin_creates_organization_and_admin_cannot(client):
    from tests.conftest import login

    admin, _ = login(client, "admin-a")
    denied = client.post("/api/v1/organizations", headers=admin, json={"name": "Organisation C"})
    assert denied.status_code == 403

    headers, _ = login(client, "super-admin")
    created = client.post("/api/v1/organizations", headers=headers, json={"name": " Organisation C "})
    assert created.status_code == 201
    organization = created.json()["data"]
    assert organization["name"] == "Organisation C"
    assert organization["slug"] == "organisation-c"
    listed = client.get("/api/v1/organizations", headers=headers).json()["data"]
    assert {item["name"] for item in listed} >= {"Demo Organization A", "Demo Organization B", "Organisation C"}
    admin_list = client.get("/api/v1/organizations", headers=admin).json()["data"]
    assert all(item["id"] != organization["id"] for item in admin_list)

    duplicate = client.post("/api/v1/organizations", headers=headers, json={"name": "organisation c"})
    assert duplicate.status_code == 409

    member = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "user_key": "operateur-1",
            "display_name": "Opérateur 1",
            "memberships": [{"organization_id": organization["id"], "role": "operator"}],
        },
    )
    assert member.status_code == 201
