"""
tool_registry.py — Defines all tools available to the Gemini agent and orchestrator

Architectural decision:
- Schema definitions provide JSON schema formats for Gemini function calling.
- TOOL_MAP connects tool names to their async Python implementations in app/tools/.
- execute_tool() enforces security classification:
    * READ actions execute automatically.
    * WRITE actions execute or create staged state.
    * SENSITIVE actions (send_email, delete_event) are BLOCKED unless bypass_approval=True.
"""

import inspect
from typing import Any, Callable, Coroutine
from app.utils.logging import get_logger
from app.tools import gmail, calendar, drive

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────
# Tool schemas (for Gemini function calling)
# ─────────────────────────────────────────────────────────────

GMAIL_TOOLS = [
    {
        "name": "search_emails",
        "description": "Search the user's Gmail inbox using a query string.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query (e.g. 'from:boss subject:report')"},
                "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_email",
        "description": "Get the full content of a specific email by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "email_id": {"type": "string", "description": "The Gmail message ID"},
            },
            "required": ["email_id"],
        },
    },
    {
        "name": "create_draft",
        "description": "Create an email draft (does NOT send it). Returns the draft ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address(es)"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
                "cc": {"type": "string", "description": "CC recipients (optional)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "send_email",
        "description": "SENSITIVE: Send an email. Always requires explicit user approval before calling.",
        "parameters": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "string", "description": "ID of a previously created draft to send"},
            },
            "required": ["draft_id"],
        },
    },
]

CALENDAR_TOOLS = [
    {
        "name": "list_events",
        "description": "List calendar events within a time range.",
        "parameters": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "description": "Start time in ISO 8601 format"},
                "time_max": {"type": "string", "description": "End time in ISO 8601 format"},
                "max_results": {"type": "integer", "description": "Maximum number of events", "default": 10},
            },
            "required": ["time_min", "time_max"],
        },
    },
    {
        "name": "find_free_time",
        "description": "Find available time slots in the user's calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date to check (YYYY-MM-DD)"},
                "duration_minutes": {"type": "integer", "description": "Required free slot duration"},
            },
            "required": ["date", "duration_minutes"],
        },
    },
    {
        "name": "create_event",
        "description": "WRITE: Create a new calendar event. Mention to user before creating.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start_time": {"type": "string", "description": "Start time in ISO 8601"},
                "end_time": {"type": "string", "description": "End time in ISO 8601"},
                "description": {"type": "string", "description": "Event description"},
                "attendees": {"type": "string", "description": "Comma-separated email addresses"},
            },
            "required": ["title", "start_time", "end_time"],
        },
    },
]

DRIVE_TOOLS = [
    {
        "name": "search_files",
        "description": "Search Google Drive for files matching a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (file name, type, etc.)"},
                "max_results": {"type": "integer", "description": "Maximum results", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_file_metadata",
        "description": "Get metadata for a specific Drive file.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID"},
            },
            "required": ["file_id"],
        },
    },
    {
        "name": "get_file_content",
        "description": "Get the text content of a Google Drive document.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "Google Drive file ID"},
            },
            "required": ["file_id"],
        },
    },
]

ALL_TOOLS = GMAIL_TOOLS + CALENDAR_TOOLS + DRIVE_TOOLS

# ─────────────────────────────────────────────────────────────
# Required Parameters per Tool
# ─────────────────────────────────────────────────────────────

REQUIRED_TOOL_PARAMS: dict[str, list[str]] = {
    t["name"]: t.get("parameters", {}).get("required", [])
    for t in ALL_TOOLS
}


# ─────────────────────────────────────────────────────────────
# Security Classification
# ─────────────────────────────────────────────────────────────

# Tools that always require human approval before execution
SENSITIVE_TOOLS = {"send_email", "delete_event"}

# Tools that are write operations
WRITE_TOOLS = {"create_draft", "create_event", "update_event"}

# Tools that are read-only (can execute automatically)
READ_TOOLS = {
    "search_emails", "get_email",
    "list_events", "find_free_time",
    "search_files", "get_file_metadata", "get_file_content",
}


def classify_tool(tool_name: str) -> str:
    """
    Returns the action classification for a given tool name.
    Returns: 'sensitive' | 'write' | 'read' | 'unknown'
    """
    if tool_name in SENSITIVE_TOOLS:
        return "sensitive"
    if tool_name in WRITE_TOOLS:
        return "write"
    if tool_name in READ_TOOLS:
        return "read"
    return "unknown"


# ─────────────────────────────────────────────────────────────
# Tool Execution Mapping
# ─────────────────────────────────────────────────────────────

TOOL_MAP: dict[str, Callable[..., Coroutine[Any, Any, dict]]] = {
    # Gmail
    "search_emails": gmail.search_emails,
    "get_email": gmail.get_email,
    "create_draft": gmail.create_draft,
    "send_email": gmail.send_email,
    # Calendar
    "list_events": calendar.list_events,
    "find_free_time": calendar.find_free_time,
    "create_event": calendar.create_event,
    # Drive
    "search_files": drive.search_files,
    "get_file_metadata": drive.get_file_metadata,
    "get_file_content": drive.get_file_content,
}


async def execute_tool(
    tool_name: str,
    args: dict[str, Any],
    bypass_approval: bool = False,
    credentials=None,
) -> dict[str, Any]:
    """
    Safely executes a tool by name with parameter validation and security checks.

    Safety:
    - Pre-validates required arguments against schema.
    - If tool is SENSITIVE and bypass_approval=False, execution is BLOCKED and
      returns status="awaiting_approval".
    - Propagates tool failures with status="error" without wrapping them as success.
    - Handles exceptions cleanly without crashing the agent.
    """
    if tool_name not in TOOL_MAP:
        logger.warning(f"Attempted to execute unknown tool: '{tool_name}'")
        return {
            "status": "error",
            "message": f"Tool '{tool_name}' does not exist.",
            "tool": tool_name,
        }

    classification = classify_tool(tool_name)

    # 1. Validate required parameters before execution
    missing_params = [
        p for p in REQUIRED_TOOL_PARAMS.get(tool_name, [])
        if p not in args or args[p] is None or args[p] == ""
    ]
    if missing_params:
        err_msg = f"Missing required parameter(s) for tool '{tool_name}': {', '.join(missing_params)}"
        logger.warning(err_msg)
        return {
            "status": "error",
            "message": err_msg,
            "tool": tool_name,
            "classification": classification,
        }

    # 2. Enforce human-in-the-loop security boundary
    if classification == "sensitive" and not bypass_approval:
        logger.info(f"Execution blocked for sensitive tool '{tool_name}' awaiting approval")
        return {
            "status": "awaiting_approval",
            "message": f"Action '{tool_name}' requires explicit user approval before execution.",
            "tool": tool_name,
            "args": args,
            "requires_approval": True,
        }

    func = TOOL_MAP[tool_name]
    try:
        logger.info(f"Executing tool '{tool_name}' (type={classification}) with args={args}")
        sig = inspect.signature(func)
        has_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

        if has_var_kwargs:
            call_args = dict(args)
        else:
            call_args = {k: v for k, v in args.items() if k in sig.parameters}

        if "credentials" in sig.parameters or has_var_kwargs:
            call_args["credentials"] = credentials

        result = await func(**call_args)

        # 3. Propagate tool errors without wrapping as success
        if isinstance(result, dict) and result.get("status") == "error":
            err_msg = result.get("message", f"Tool '{tool_name}' returned an error")
            logger.warning(f"Tool '{tool_name}' execution returned error: {err_msg}")
            return {
                "status": "error",
                "message": err_msg,
                "tool": tool_name,
                "classification": classification,
                "data": result,
            }

        return {
            "status": "success",
            "tool": tool_name,
            "classification": classification,
            "data": result,
        }
    except TypeError as te:
        # Signature mismatch / missing required arguments
        logger.error(f"Parameter error calling '{tool_name}': {te}")
        return {
            "status": "error",
            "message": f"Invalid arguments for tool '{tool_name}': {str(te)}",
            "tool": tool_name,
            "classification": classification,
        }
    except Exception as e:
        logger.error(f"Error executing tool '{tool_name}': {e}")
        return {
            "status": "error",
            "message": f"Tool execution failed: {str(e)}",
            "tool": tool_name,
            "classification": classification,
        }
