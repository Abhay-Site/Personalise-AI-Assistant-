"""
tests/test_master_demo.py — End-to-End Master Demo Journey Test

Tests the full lifecycle of ORBIT 180:
1. Health & system readiness
2. Morning briefing retrieval
3. Memory injection and persistence
4. Multi-app prompt planning & glass-box execution (Calendar + Drive + Gmail)
5. Sensitive action pausing & Human-in-the-Loop approval
6. Audit log recording & secret sanitization
"""

def test_full_master_demo_journey(client):
    # ── Step 1: Verify System Health ─────────────────────────
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # ── Step 2: Retrieve Morning Briefing ─────────────────────
    briefing_resp = client.get("/api/briefing")
    assert briefing_resp.status_code == 200
    briefing = briefing_resp.json()
    assert "greeting" in briefing
    assert len(briefing["events"]) > 0

    # ── Step 3: Set User Memory Preference ────────────────────
    mem_resp = client.post("/api/memory", json={
        "key": "preferred_study_hours",
        "value": "2 PM to 5 PM",
        "category": "scheduling"
    })
    assert mem_resp.status_code == 201
    mem_id = mem_resp.json()["id"]

    # ── Step 4: Execute Master Cross-App Prompt ───────────────
    master_prompt = (
        "Find tomorrow's project review meeting, locate the latest ORBIT 180 report, "
        "and prepare an email for the participants"
    )
    chat_resp = client.post("/api/chat", json={"message": master_prompt})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()

    # Verify Action Plan decomposition
    plan = chat_data["action_plan"]
    assert plan is not None
    assert len(plan["steps"]) == 4
    assert plan["steps"][0]["service"] == "calendar"
    assert plan["steps"][1]["service"] == "drive"
    assert plan["steps"][2]["service"] == "gmail"
    assert plan["steps"][3]["action"] == "send_email"
    assert plan["steps"][3]["requires_approval"] is True

    # Verify Human-in-the-Loop Security Pause
    assert chat_data["requires_approval"] is True
    assert chat_data["approval_action"]["type"] == "send_email"
    plan_id = chat_data["action_plan_id"]
    assert plan_id is not None

    # Verify Glass-box Trace
    trace = chat_data["trace"]
    assert any("Calendar" in t["message"] for t in trace)
    assert any("Drive" in t["message"] or "search_files" in t["message"] for t in trace)
    assert any("draft" in t["message"].lower() for t in trace)

    # ── Step 5: User Approves Sensitive Action ────────────────
    approval_resp = client.post("/api/approvals", json={
        "action_plan_id": plan_id,
        "approved": True
    })
    assert approval_resp.status_code == 200
    approval_data = approval_resp.json()
    assert approval_data["status"] == "executed"
    assert approval_data["approved"] is True

    # ── Step 6: Verify Immutable Audit Trail ──────────────────
    audit_resp = client.get("/api/audit?approval_status=approved")
    assert audit_resp.status_code == 200
    approved_logs = audit_resp.json()
    assert len(approved_logs) > 0
    assert any(l["tool_name"] == "send_email" for l in approved_logs)

    # Cleanup created memory
    del_resp = client.delete(f"/api/memory/{mem_id}")
    assert del_resp.status_code == 204
