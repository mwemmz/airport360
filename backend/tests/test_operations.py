"""Phase 2-4 tests: operational intelligence, passenger app, booking marketplace."""


def test_ops_overview(ku_ops_headers, client):
    resp = client.get("/v1/ops/overview", headers=ku_ops_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["site_id"] == 1
    assert body["risk_level"]["level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert body["risk_level"]["rule"]
    assert body["timeline"], "event timeline should be populated"
    assert body["label"] == "Simulated operational data"


def test_ops_overview_blocks_staff(ku_staff_headers, client):
    resp = client.get("/v1/ops/overview", headers=ku_staff_headers)
    assert resp.status_code == 403


def test_ops_isolation_ops_cannot_read_other_site(nm_ops_headers, client):
    resp = client.get("/v1/ops/overview?site_id=1", headers=nm_ops_headers)
    assert resp.status_code == 403


def test_executive_cross_site_ops(exec_headers, client):
    resp = client.get("/v1/ops/overview?site_id=2", headers=exec_headers)
    assert resp.status_code == 200
    assert resp.json()["site_id"] == 2


def test_flights_list_and_status_update(ku_ops_headers, client):
    resp = client.get("/v1/flights", headers=ku_ops_headers)
    assert resp.status_code == 200
    flights = resp.json()
    assert len(flights) >= 10
    flight_id = flights[0]["id"]
    update = client.patch(f"/v1/flights/{flight_id}/status", params={"status": "Boarding"}, headers=ku_ops_headers)
    assert update.status_code == 200
    assert update.json()["status"] == "Boarding"


def test_queue_prediction(ku_ops_headers, client):
    resp = client.get("/v1/predictions/queue", params={"queue_type": "security", "horizon_minutes": 30}, headers=ku_ops_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_length"] >= 0
    assert body["congestion_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert body["metrics"] is not None
    assert body["model_name"] == "queue_prediction"


def test_queue_prediction_requires_history(client, ku_ops_headers):
    # A second site with no queue samples should refuse training
    resp = client.get("/v1/predictions/queue?site_id=999", headers=ku_ops_headers)
    assert resp.status_code in (403, 404, 409)


def test_baggage_list_and_risk(ku_ops_headers, client):
    resp = client.get("/v1/baggage", headers=ku_ops_headers)
    assert resp.status_code == 200
    rows = resp.json()
    assert rows
    assert all(0.0 <= r["risk_score"] <= 1.0 for r in rows)
    assert all("prototype risk model" in r["tag"].lower() for r in rows)


def test_baggage_high_risk_endpoint(ku_ops_headers, client):
    resp = client.get("/v1/baggage/high-risk", headers=ku_ops_headers)
    assert resp.status_code == 200
    for row in resp.json():
        assert row["risk_score"] >= 0.5


def test_incidents_crud_and_escalation(ku_ops_headers, client, db):
    created = client.post(
        "/v1/incidents",
        params={
            "category": "security",
            "title": "Test critical incident",
            "description": "Seeded long ago",
            "severity": "CRITICAL",
        },
        headers=ku_ops_headers,
    )
    assert created.status_code == 200
    incident_id = created.json()["id"]

    from datetime import datetime, timedelta, timezone

    from app.models.operations import Incident

    incident = db.get(Incident, incident_id)
    incident.reported_at = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()

    resp = client.post(f"/v1/incidents/{incident_id}/escalate", headers=ku_ops_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["escalation_logged"] is True

    resolved = client.post(f"/v1/incidents/{incident_id}/resolve", headers=ku_ops_headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "Resolved"


def test_incident_escalation_rejected_when_fresh(ku_ops_headers, client):
    created = client.post(
        "/v1/incidents",
        params={"category": "medical", "title": "Fresh critical", "description": "just now", "severity": "CRITICAL"},
        headers=ku_ops_headers,
    )
    incident_id = created.json()["id"]
    resp = client.post(f"/v1/incidents/{incident_id}/escalate", headers=ku_ops_headers)
    assert resp.status_code == 409


def test_maintenance_repeat_failure(ku_ops_headers, client, db):
    from datetime import datetime, timedelta

    from app.models.operations import MaintenanceRequest

    # Build two resolved requests with the same repeat key, then check detection
    for i in range(2):
        db.add(
            MaintenanceRequest(
                site_id=1,
                request_number=f"MTN-TEST-{i}",
                category="toilet",
                priority="Medium",
                status="Resolved",
                location="Toilet Block Z",
                description="x",
                reported_by="ops.ku@airport360.com",
                source="Staff",
                reported_at=datetime.now() - timedelta(days=10),
                resolved_at=datetime.now() - timedelta(days=9),
                repeat_key="toilet|toilet block z",
            )
        )
    db.commit()

    resp = client.get("/v1/maintenance/repeat-failures", headers=ku_ops_headers)
    assert resp.status_code == 200
    assert any(r["repeat_key"] == "toilet|toilet block z" for r in resp.json())

    created = client.post(
        "/v1/maintenance",
        params={"category": "toilet", "location": "Toilet Block Z"},
        headers=ku_ops_headers,
    )
    assert created.status_code == 200
    assert created.json()["repeat_failure"] is True


def test_alerts_dedup(ku_ops_headers, client):
    first = client.post("/v1/alerts", params={"title": "Dup test", "severity": "HIGH", "alert_type": "congestion"}, headers=ku_ops_headers)
    assert first.status_code == 200
    assert first.json()["deduped"] is False

    second = client.post("/v1/alerts", params={"title": "Dup test", "severity": "HIGH", "alert_type": "congestion"}, headers=ku_ops_headers)
    assert second.status_code == 200
    assert second.json()["deduped"] is True
    assert second.json()["id"] == first.json()["id"]


def test_alerts_auto_from_critical_incidents(ku_ops_headers, client, db):
    from datetime import datetime, timedelta, timezone

    from app.models.operations import Incident

    db.add(
        Incident(
            site_id=1,
            incident_number="INC-AUTO-0001",
            category="fire",
            severity="CRITICAL",
            status="Reported",
            title="Fire alarm in check-in hall",
            description="auto alert trigger",
            reported_by="ops.ku@airport360.com",
            source="Staff",
            reported_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
    )
    db.commit()

    resp = client.post("/v1/alerts/auto", headers=ku_ops_headers)
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()["created"]]
    assert any("Fire alarm in check-in hall" in t for t in titles)


def test_ai_recommendations_and_answer(ku_ops_headers, client):
    recs = client.get("/v1/ai/recommendations", headers=ku_ops_headers)
    assert recs.status_code == 200
    assert recs.json(), "recommendations should be non-empty"

    ans = client.get("/v1/ai/answer", params={"question": "predict the security queue"}, headers=ku_ops_headers)
    assert ans.status_code == 200
    body = ans.json()
    assert body["facts"]
    assert "queue" in body["answer"].lower() or "no data" in body["answer"].lower()


def test_passenger_flight_and_baggage_status(ku_passenger_headers, client, db):
    from sqlalchemy import select

    from app.models.operations import Passenger

    reference = db.scalar(select(Passenger.passenger_reference).where(Passenger.site_id == 1))
    assert reference

    flight = client.get("/v1/passenger/flight-status", params={"reference": reference}, headers=ku_passenger_headers)
    assert flight.status_code == 200
    assert flight.json()["flight_number"]

    bags = client.get("/v1/passenger/baggage", params={"reference": reference}, headers=ku_passenger_headers)
    assert bags.status_code in (200, 404)

    complaint = client.post(
        "/v1/passenger/complaints",
        params={"category": "baggage", "title": "Delayed bag", "reference": reference, "description": "Still waiting"},
        headers=ku_passenger_headers,
    )
    assert complaint.status_code == 200
    assert complaint.json()["status"] == "Submitted"


def test_passenger_cannot_access_ops(ku_passenger_headers, client):
    resp = client.get("/v1/ops/overview", headers=ku_passenger_headers)
    assert resp.status_code == 403


def test_complaints_resolve_links_incident(ku_ops_headers, client):
    resp = client.get("/v1/complaints", headers=ku_ops_headers)
    assert resp.status_code == 200
    complaints = resp.json()
    assert complaints
    cid = complaints[0]["id"]
    resolved = client.post(f"/v1/complaints/{cid}/resolve", params={"create_incident": True}, headers=ku_ops_headers)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "Resolved"
    assert resolved.json()["linked_incident_id"] is not None


def test_bookings_partners_and_referral(ku_ops_headers, client):
    partners = client.get("/v1/bookings/partners", headers=ku_ops_headers)
    assert partners.status_code == 200
    assert partners.json()
    pid = partners.json()[0]["id"]

    referral = client.post(
        "/v1/bookings/referrals",
        params={
            "partner_id": pid,
            "airline": "KuAir",
            "origin": "LVI",
            "destination": "JNB",
            "passenger_reference": "PASS-TEST-0001",
            "redirect_url": "https://partner.example.com/book",
        },
        headers=ku_ops_headers,
    )
    assert referral.status_code == 200, referral.text
    assert referral.json()["redirect_url"].startswith("https://")

    bad = client.post(
        "/v1/bookings/referrals",
        params={
            "partner_id": pid,
            "airline": "KuAir",
            "origin": "LVI",
            "destination": "JNB",
            "passenger_reference": "PASS-TEST-0002",
            "redirect_url": "http://insecure.example.com",
        },
        headers=ku_ops_headers,
    )
    assert bad.status_code == 400


def test_bookings_analytics_admin(admin_headers, client):
    resp = client.get("/v1/bookings/analytics", headers=admin_headers)
    assert resp.status_code == 200
    assert "total_referrals" in resp.json()


def test_cargo_list(ku_ops_headers, client):
    resp = client.get("/v1/cargo", headers=ku_ops_headers)
    assert resp.status_code == 200
    assert resp.json()
