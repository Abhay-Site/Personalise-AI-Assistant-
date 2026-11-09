"""
orchestrator.py — The central AI agent and tool execution pipeline

Flow:
  1. Receive user message
  2. Load user preferences/memories and inject into prompt context
  3. Formulate structured ActionPlan (decomposing multi-step or cross-app requests)
  4. Glass-box execution loop:
     - Execute safe READ/WRITE operations in sequence
     - Record friendly human-readable TraceStep entries
     - Detect SENSITIVE operations (e.g. send_email, delete_event)
     - PAUSE execution before sensitive operations and flag requires_approval=True
  5. AI Response Synthesis:
     - Feed context, memory, and tool execution outputs to Gemini
     - Gemini formats a helpful, explainable response
  6. Return structured ChatResponse with reply, action plan, and execution trace
"""

from typing import Any, Optional
import google.generativeai as genai
from app.agents.prompts import ORBIT_SYSTEM_PROMPT, build_context_prompt
from app.agents.planner import build_plan_from_intent
from app.agents.tool_registry import classify_tool, execute_tool
from app.services.workflow_service import WorkflowContext
from app.services.privacy_shield import redact_pii
from app.schemas.chat import TraceStep, ActionPlanSchema
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _configure_gemini() -> bool:
    """Configures the Gemini SDK if GEMINI_API_KEY is available."""
    settings = get_settings()
    if not settings.gemini_configured:
        logger.info("GEMINI_API_KEY not set — using local rule-based response synthesizer.")
        return False
    try:
        genai.configure(api_key=settings.gemini_api_key)
        return True
    except Exception as e:
        logger.error(f"Failed to configure Gemini: {e}")
        return False


def _synthesize_local_response(
    user_message: str,
    action_plan: Optional[ActionPlanSchema],
    tool_results: list[dict[str, Any]],
    requires_approval: bool,
    approval_action: Optional[dict[str, Any]],
) -> str:
    """
    Produces a clean, intelligent response when no Gemini API key is configured.
    Provides complete end-to-end usability and transparency during local testing.
    """
    if not action_plan:
        return (
            f"I understood: \"{user_message}\"\n\n"
            "I'm ORBIT 180 — your observable, memory-augmented productivity agent. "
            "You can ask me to coordinate across Gmail, Google Calendar, and Drive!\n\n"
            "Try: *\"Find tomorrow's project review meeting, locate the latest ORBIT 180 report, and prepare an email for the participants.\"*"
        )

    parts: list[str] = [f"I have created an action plan for: **{action_plan.goal}**\n"]

    if tool_results:
        parts.append("### Completed Actions & Retrieved Data:")
        for res in tool_results:
            tool_name = res.get("tool", "action")
            classification = res.get("classification", "read")
            tool_data = res.get("data", {})
            data_mode = tool_data.get("status", "unknown") if isinstance(tool_data, dict) else "unknown"
            mode_badge = " [Simulated / Demo Mode]" if data_mode == "demo" else " [Live Google API]"
            parts.append(f"• **{tool_name}** ({classification}){mode_badge}: executed successfully")
            if isinstance(tool_data, dict):
                if "events" in tool_data:
                    for ev in tool_data["events"]:
                        parts.append(f"  - **Meeting**: {ev.get('summary')} | **Time**: {ev.get('start')} – {ev.get('end')} | **Attendees**: {', '.join(ev.get('attendees', []))} | **Status**: {mode_badge.strip()}")
                if "files" in tool_data:
                    for f in tool_data["files"]:
                        parts.append(f"  - **File**: {f.get('name')} | **Modified**: {f.get('modified_time')} | **Link**: {f.get('link')} | **Status**: {mode_badge.strip()}")
                if "emails" in tool_data:
                    for em in tool_data["emails"]:
                        parts.append(f"  - **Email**: Subject: '{em.get('subject')}' from {em.get('sender')} | **Status**: {mode_badge.strip()}")
        parts.append("")

    if requires_approval and approval_action:
        action_name = approval_action.get("type", "Sensitive action")
        desc = approval_action.get("description", "Requires confirmation")
        parts.append(
            f"⚠️ **Approval Required Before Execution:**\n"
            f"The action **`{action_name}`** ({desc}) is classified as **SENSITIVE**.\n"
            f"Please review and click **Approve** to dispatch or **Reject** to cancel."
        )
    else:
        parts.append("All scheduled read operations completed successfully.")

    return "\n".join(parts)


async def process_message(
    user_message: str,
    memories: list[dict],
    conversation_history: list[dict],
    credentials: Any = None,
    user_id: Optional[int] = None,
) -> dict:
    """
    Main entry point for the AI agent execution pipeline.

    Args:
        user_message: The raw natural-language request from the user
        memories: Active user preferences and rules from memory service
        conversation_history: Prior conversation turns

    Returns:
        Dictionary conforming to the ChatResponse schema.
    """
    trace: list[TraceStep] = []
    settings = get_settings()

    # ── Step 1: Memory Context Retrieval ─────────────────────
    trace.append(TraceStep(status="ok", message="Retrieving user preferences and rules from memory"))
    context_prompt = build_context_prompt(memories)
    if memories:
        trace.append(TraceStep(
            status="ok",
            message=f"Applied {len(memories)} active memory preferences to planning context",
            detail=", ".join(m["key"] for m in memories),
        ))

    # ── Step 2: Formulate Action Plan ─────────────────────────
    trace.append(TraceStep(status="ok", message="Decomposing user request into sequential action plan"))
    action_plan = await build_plan_from_intent(user_message)

    tool_results: list[dict[str, Any]] = []
    requires_approval = False
    approval_action = None

    # ── Step 3: Glass-Box Execution Loop ─────────────────────
    if action_plan:
        workflow_ctx = WorkflowContext()
        trace.append(TraceStep(
            status="ok",
            message=f"Created {len(action_plan.steps)}-step action plan across services",
            detail=action_plan.goal,
        ))

        for step in action_plan.steps:
            classification = classify_tool(step.action)

            # Determine base arguments
            base_args: dict[str, Any] = {}
            if step.action == "search_emails":
                query = "meeting"
                for w in ["deadline", "assignment", "homework", "urgent", "professor", "project", "review", "exam"]:
                    if w in user_message.lower():
                        query = w
                        break
                base_args = {"query": query, "max_results": 5}
            elif step.action == "find_free_time":
                from datetime import datetime, timezone, timedelta
                now = datetime.now(timezone.utc)
                msg_lower = user_message.lower()
                target_date = (now + timedelta(days=1)).strftime("%Y-%m-%d") if "tomorrow" in msg_lower else now.strftime("%Y-%m-%d")
                base_args = {"date": target_date, "duration_minutes": 60}
            elif step.action == "list_events":
                from datetime import datetime, timezone, timedelta
                import re

                now = datetime.now(timezone.utc)
                msg_lower = user_message.lower()

                # Check for explicit ISO date (YYYY-MM-DD)
                iso_match = re.search(r'\b(202\d-\d{2}-\d{2})\b', user_message)

                if iso_match:
                    try:
                        parsed_day = datetime.fromisoformat(iso_match.group(1)).replace(tzinfo=timezone.utc)
                        start_date = parsed_day.replace(hour=0, minute=0, second=0, microsecond=0)
                        end_date = parsed_day.replace(hour=23, minute=59, second=59, microsecond=0)
                    except Exception:
                        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                        end_date = (start_date + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
                elif "tomorrow" in msg_lower:
                    start_date = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=0)
                elif "today" in msg_lower:
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=0)
                elif "yesterday" in msg_lower:
                    start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=0)
                elif "this week" in msg_lower or "next week" in msg_lower:
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = (start_date + timedelta(days=7)).replace(hour=23, minute=59, second=59, microsecond=0)
                else:
                    # Default: search upcoming meetings from today through the next 2 days
                    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = (start_date + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=0)

                time_min = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                time_max = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
                base_args = {"time_min": time_min, "time_max": time_max, "max_results": 5}
            elif step.action == "search_files":
                base_args = {"query": "ORBIT 180 report", "max_results": 5}
            elif step.action == "create_draft":
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', user_message)
                subj_match = re.search(r"subject\s*['\":]?\s*([^'\"]+?)(?:\s*(?:saying|body|with body|message|content)|\s*$)", user_message, re.IGNORECASE)
                body_match = re.search(r"(?:saying|body|content|message)\s*['\":]?\s*(.+?)(?:['\"]\s*$|$)", user_message, re.IGNORECASE)

                extracted_to = email_match.group(0) if email_match else "team@orbit180.dev"

                if subj_match:
                    extracted_subj = subj_match.group(1).strip(" '\"")
                elif "meeting" in user_message.lower() or "scheducle" in user_message.lower() or "schedule" in user_message.lower():
                    time_match = re.search(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', user_message, re.IGNORECASE)
                    time_str = f" at {time_match.group(0).upper()}" if time_match else ""
                    extracted_subj = f"Meeting Schedule{time_str} Confirmation"
                else:
                    extracted_subj = "Project Review Meeting & Report"

                if body_match:
                    extracted_body = body_match.group(1).strip(" '\"")
                elif "meeting" in user_message.lower() or "scheducle" in user_message.lower() or "schedule" in user_message.lower():
                    time_match = re.search(r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', user_message, re.IGNORECASE)
                    time_str = time_match.group(0).upper() if time_match else "10:00 AM"
                    day_str = "today" if "today" in user_message.lower() else "as scheduled"
                    extracted_body = (
                        f"Hello,\n\n"
                        f"This is a confirmation that our meeting is scheduled for {day_str} at {time_str}.\n\n"
                        f"Please let me know if you need any further information beforehand.\n\n"
                        f"Best regards,\n"
                        f"ORBIT 180"
                    )
                else:
                    extracted_body = "Attached is the latest report for your review."

                base_args = {
                    "to": extracted_to,
                    "subject": extracted_subj,
                    "body": extracted_body,
                }

            # Enrich arguments dynamically using context from prior steps
            args = workflow_ctx.resolve_tool_args(step.action, base_args)

            if step.action == "create_draft" and user_id is not None:
                args["user_id"] = user_id

            if step.action == "send_email":
                if user_id is not None:
                    args["user_id"] = user_id
                draft_id = args.get("draft_id")
                from app.tools.gmail import _PENDING_DRAFTS
                if draft_id and draft_id in _PENDING_DRAFTS:
                    d = _PENDING_DRAFTS[draft_id]
                    if not args.get("to") and d.get("to"):
                        args["to"] = d.get("to")
                    if not args.get("subject") and d.get("subject"):
                        args["subject"] = d.get("subject")
                    if not args.get("body") and d.get("body"):
                        args["body"] = d.get("body")

            # Check if this step is sensitive and requires human-in-the-loop approval
            step.args = args
            if classification == "sensitive" or step.requires_approval:
                step.status = "awaiting_approval"
                requires_approval = True
                approval_action = {
                    "type": step.action,
                    "service": step.service,
                    "description": step.description,
                    "order": step.order,
                    "args": args,
                }
                trace.append(TraceStep(
                    status="warning",
                    message=f"Paused before sensitive action: '{step.action}'",
                    detail=f"{step.service.upper()}: {step.description}. Awaiting human approval.",
                ))
                # Security boundary: Do not execute sensitive steps automatically
                break

            # Execute safe READ or WRITE step
            trace.append(TraceStep(
                status="ok",
                message=f"Executing {step.service.capitalize()}: {step.action}",
                detail=step.description,
            ))

            res = await execute_tool(step.action, args, bypass_approval=False, credentials=credentials)
            
            # Record result in workflow context for downstream steps
            workflow_ctx.record_step_result(step.action, res)

            # Check for error status to prevent cascade failures
            if res.get("status") == "error":
                step.status = "failed"
                trace.append(TraceStep(
                    status="error",
                    message=f"Step failed: {step.action}",
                    detail=res.get("message", "API call returned an error"),
                ))
                break

            step.status = "done"
            tool_results.append(res)
            trace.append(TraceStep(
                status="ok",
                message=f"Completed {step.action} successfully",
            ))

    # ── Step 4: AI Response Synthesis ────────────────────────
    trace.append(TraceStep(status="ok", message="Synthesizing final response"))
    gemini_available = _configure_gemini()

    if not gemini_available:
        integration_status = "demo"
        model_name = "local_synthesizer"
        is_fallback = True
        error_detail = "GEMINI_API_KEY is not configured in backend/.env — running in Demo Simulation mode."
        reply = _synthesize_local_response(
            user_message=user_message,
            action_plan=action_plan,
            tool_results=tool_results,
            requires_approval=requires_approval,
            approval_action=approval_action,
        )
        trace.append(TraceStep(
            status="warning",
            message="Running in Demo Simulation mode (GEMINI_API_KEY not configured)",
            detail=error_detail,
        ))
    else:
        candidate_models = [settings.gemini_model, "gemini-flash-lite-latest", "gemini-3.5-flash-lite"]
        candidate_models = list(dict.fromkeys(candidate_models))

        # Build prior dialogue history
        history = []
        for msg in conversation_history[:-1]:
            history.append({
                "role": "model" if msg["role"] == "assistant" else msg["role"],
                "parts": [msg["content"]],
            })

        # Prepare structured context for Gemini
        execution_summary = ""
        if tool_results:
            import json
            summary_lines = ["\n## Tool Results (Data retrieved from user's services):"]
            for r in tool_results:
                tool_name = r.get("tool", "tool")
                tool_data = r.get("data", {})
                data_mode = tool_data.get("status", "unknown") if isinstance(tool_data, dict) else "unknown"
                mode_label = "SIMULATED / DEMO MODE" if data_mode == "demo" else "REAL / LIVE GOOGLE"
                summary_lines.append(f"\n### Tool: {tool_name} [{mode_label}]")
                if isinstance(tool_data, dict):
                    if "events" in tool_data:
                        summary_lines.append(f"- Calendar Events (Source: {mode_label}): {json.dumps(tool_data.get('events'))}")
                    if "files" in tool_data:
                        summary_lines.append(f"- Drive Files (Source: {mode_label}): {json.dumps(tool_data.get('files'))}")
                    if "emails" in tool_data:
                        summary_lines.append(f"- Gmail Emails (Source: {mode_label}): {json.dumps(tool_data.get('emails'))}")
                    if "message" in tool_data and not any(k in tool_data for k in ["events", "files", "emails"]):
                        summary_lines.append(f"- Message: {tool_data.get('message')}")
                else:
                    summary_lines.append(f"- Output: {str(tool_data)}")
            execution_summary = "\n".join(summary_lines) + "\n"
        if requires_approval and approval_action:
            execution_summary += (
                f"\n## PENDING APPROVAL:\nAction '{approval_action['type']}' "
                f"({approval_action['description']}) is awaiting explicit user approval.\n"
            )

        full_prompt = f"{context_prompt}{execution_summary}\n\nUser Request: {user_message}"
        
        # Apply Privacy Shield PII Redaction
        sanitized_prompt, redacted_entities = redact_pii(full_prompt, enabled=True)
        if redacted_entities:
            trace.append(TraceStep(
                status="ok",
                message=f"🛡 Privacy Shield redacted PII: {', '.join(set(redacted_entities))}",
            ))

        reply = None
        used_model = None
        model_errors = []

        for m_name in candidate_models:
            try:
                model = genai.GenerativeModel(
                    model_name=m_name,
                    system_instruction=ORBIT_SYSTEM_PROMPT,
                )
                chat = model.start_chat(history=history)
                response = chat.send_message(
                    sanitized_prompt,
                    generation_config={"max_output_tokens": 350, "temperature": 0.2},
                )
                reply = response.text
                used_model = m_name
                break
            except Exception as m_err:
                err_str = str(m_err)
                model_errors.append(f"{m_name}: {err_str}")
                logger.warning(f"Gemini model {m_name} error: {err_str}")
                continue

        if reply:
            integration_status = "connected"
            model_name = used_model
            is_fallback = False
            error_detail = None
            trace.append(TraceStep(status="ok", message=f"Response generated by Google Gemini ({used_model})"))
        else:
            integration_status = "fallback"
            model_name = "local_fallback"
            is_fallback = True

            first_err = model_errors[0] if model_errors else "API call failure"
            if "429" in first_err or "Quota exceeded" in first_err:
                error_detail = "Google Gemini API rate limit or quota exceeded (429). The system temporarily fell back to the local agent synthesizer."
            elif "403" in first_err or "API_KEY_INVALID" in first_err:
                error_detail = "Google Gemini authentication error (403/invalid key). Please verify GEMINI_API_KEY in backend/.env."
            else:
                error_detail = f"Gemini API error: {first_err[:180]}. Fell back to local agent synthesizer."

            reply = _synthesize_local_response(
                user_message=user_message,
                action_plan=action_plan,
                tool_results=tool_results,
                requires_approval=requires_approval,
                approval_action=approval_action,
            )
            trace.append(TraceStep(
                status="error",
                message="Google Gemini API failed — switched to local fallback synthesizer",
                detail=error_detail,
            ))

    trace.append(TraceStep(status="ok", message="Ready"))

    return {
        "reply": reply,
        "action_plan": action_plan,
        "trace": trace,
        "requires_approval": requires_approval,
        "approval_action": approval_action,
        "integration_status": integration_status,
        "model_name": model_name,
        "is_fallback": is_fallback,
        "error_detail": error_detail,
    }
