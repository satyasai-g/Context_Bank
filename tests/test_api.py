import pytest


def test_api_health(client):
    """Test health check endpoint."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_api_crud_flow(client, auth_headers_a):
    """Test API Context Creation, Retrieval, and Quick Lookup."""
    payload = {
        "trigger_word": "VOXCENT",
        "title": "Voxcent Assistant",
        "summary": "Voice first learning app.",
        "category": "Projects",
        "status": "In Progress",
        "tags": ["voice", "python"],
        "important_decisions": [{"text": "Postgres chosen", "status": "confirmed"}],
        "next_steps": ["Write unit tests"],
    }

    # 1. Create context via API
    create_resp = client.post("/api/v1/contexts", json=payload, headers=auth_headers_a)
    assert create_resp.status_code == 201
    ctx_data = create_resp.json()
    assert ctx_data["primary_trigger"] == "VOXCENT"
    ctx_id = ctx_data["id"]

    # 2. Retrieve via exact trigger endpoint
    retrieve_resp = client.post(
        "/api/v1/contexts/retrieve",
        json={"trigger": "voxcent", "detail_level": "summary_and_state", "output_format": "markdown"},
        headers=auth_headers_a,
    )
    assert retrieve_resp.status_code == 200
    pkg = retrieve_resp.json()
    assert pkg["primary_trigger"] == "VOXCENT"
    assert "Postgres chosen" in pkg["package_content"]

    # 3. Quick lookup endpoint
    lookup_resp = client.get("/api/v1/search/quick-lookup/VOXCENT", headers=auth_headers_a)
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["found"] is True

    # 4. Search endpoint (semantic & keyword)
    search_resp = client.post(
        "/api/v1/search",
        json={"query": "voice learning", "limit": 5},
        headers=auth_headers_a,
    )
    assert search_resp.status_code == 200
    s_data = search_resp.json()
    assert s_data["total_results"] >= 1
    assert s_data["results"][0]["primary_trigger"] == "VOXCENT"

    # 5. Export endpoint
    export_resp = client.post(
        f"/api/v1/contexts/{ctx_id}/export?format=json",
        headers=auth_headers_a,
    )
    assert export_resp.status_code == 200
    assert export_resp.json()["export_format"] == "json"

    # 6. Delete endpoint
    del_resp = client.delete(f"/api/v1/contexts/{ctx_id}", headers=auth_headers_a)
    assert del_resp.status_code == 200


def test_api_duplicate_trigger_conflict(client, auth_headers_a):
    """Test duplicate trigger returns 409 Conflict."""
    payload = {
        "trigger_word": "UNIQUE_KEY",
        "title": "Title 1",
        "summary": "Summary 1",
    }
    r1 = client.post("/api/v1/contexts", json=payload, headers=auth_headers_a)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/contexts", json=payload, headers=auth_headers_a)
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"]


def test_api_missing_trigger_not_found(client, auth_headers_a):
    """Test requesting non-existent trigger returns 404 with exact message."""
    resp = client.post(
        "/api/v1/contexts/retrieve",
        json={"trigger": "NON_EXISTENT", "detail_level": "summary_and_state", "output_format": "markdown"},
        headers=auth_headers_a,
    )
    assert resp.status_code == 404
    assert "No exact context registered" in resp.json()["message"]
