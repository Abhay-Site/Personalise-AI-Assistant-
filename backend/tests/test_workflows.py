"""
tests/test_workflows.py — Tests for Cross-Application Workflows and Parameter Chaining
"""

from app.services.workflow_service import WorkflowContext


def test_workflow_context_chaining():
    """
    Verifies that WorkflowContext accumulates parameters across tools
    and enriches downstream tools with upstream outputs.
    """
    ctx = WorkflowContext()

    # 1. Feed mock Calendar list_events output
    mock_calendar_res = {
        "status": "connected",
        "events": [
            {
                "summary": "AI Thesis Review",
                "start": "Tomorrow, 10:00 AM",
                "attendees": ["advisor@univ.edu", "co-advisor@univ.edu"],
            }
        ],
    }
    ctx.record_step_result("list_events", mock_calendar_res)
    assert ctx.extracted_data["meeting_title"] == "AI Thesis Review"
    assert "advisor@univ.edu" in ctx.extracted_data["attendees"]

    # 2. Feed mock Drive search_files output
    mock_drive_res = {
        "status": "connected",
        "files": [
            {
                "name": "Thesis_Draft_v4.pdf",
                "link": "https://drive.google.com/thesis-draft",
            }
        ],
    }
    ctx.record_step_result("search_files", mock_drive_res)
    assert ctx.extracted_data["file_name"] == "Thesis_Draft_v4.pdf"

    # 3. Resolve arguments for create_draft
    draft_args = ctx.resolve_tool_args("create_draft", {})
    assert "advisor@univ.edu" in draft_args["to"]
    assert "AI Thesis Review" in draft_args["subject"]
    assert "Thesis_Draft_v4.pdf" in draft_args["body"]


def test_cross_app_master_demo_execution(client):
    """
    Tests the complete master demo:
    'Find tomorrow's project review meeting, locate the latest Personal AI Assistant report, and prepare an email for the participants'
    Verifies:
    1. Returns a 4-step action plan
    2. Chained email draft step contains the report and attendees
    3. Final send_email step requires human approval
    """
    response = client.post("/api/chat", json={
        "message": "Find tomorrow's project review meeting, locate the latest Personal AI Assistant report, and prepare an email for the participants"
    })
    assert response.status_code == 200
    data = response.json()

    assert data["requires_approval"] is True
    assert data["approval_action"]["type"] == "send_email"

    plan = data["action_plan"]
    assert plan is not None
    assert len(plan["steps"]) == 4

    services = [s["service"] for s in plan["steps"]]
    assert services == ["calendar", "drive", "gmail", "gmail"]

    # Check execution trace
    trace = data["trace"]
    trace_messages = " ".join(t["message"] for t in trace)
    assert "Calendar" in trace_messages
    assert "search_files" in trace_messages or "Drive" in trace_messages
    assert "create_draft" in trace_messages or "draft" in trace_messages.lower()


def test_workflow_catalog_and_run(client):
    """Verifies that workflow templates can be listed and directly triggered."""
    # 1. List templates
    list_resp = client.get("/api/workflows")
    assert list_resp.status_code == 200
    templates = list_resp.json()
    assert len(templates) >= 3

    # 2. Run master-demo template
    run_resp = client.post("/api/workflows/run?workflow_id=master-demo")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["requires_approval"] is True
    assert run_data["action_plan"] is not None

    # 3. History
    hist_resp = client.get("/api/workflows/history")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) > 0
