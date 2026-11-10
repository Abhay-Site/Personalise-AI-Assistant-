"""
services/workflow_service.py — Cross-Application Workflow Context

Stores only data obtained from actual tool results.
Never invents meeting details, attendees, filenames, or document links.
"""

from typing import Any
from app.utils.logging import get_logger

logger = get_logger(__name__)


class WorkflowContext:
    """
    Maintains verified data across chained tool executions.
    """

    def __init__(self):
        self.extracted_data: dict[str, Any] = {
            "attendees": [],
            "meeting_title": None,
            "meeting_time": None,
            "file_name": None,
            "file_link": None,
            "draft_id": None,
        }

        self.step_outputs: list[dict[str, Any]] = []

    def record_step_result(
        self,
        tool_name: str,
        result: dict[str, Any],
    ) -> None:
        """
        Records tool results and extracts data only from successful operations.
        """

        self.step_outputs.append({
            "tool": tool_name,
            "result": result,
        })

        # Never extract data from a failed or blocked operation.
        if not isinstance(result, dict):
            logger.warning(
                "Ignoring invalid result from tool '%s'",
                tool_name,
            )
            return

        if result.get("status") in {
            "error",
            "awaiting_approval",
            "failed",
        }:
            logger.warning(
                "Ignoring unsuccessful result from tool '%s'",
                tool_name,
            )
            return

        # Handle both direct results and wrapped tool results.
        data = result.get("data", result)

        if not isinstance(data, dict):
            return

        # 1. Calendar extraction
        if tool_name == "list_events":
            events = data.get("events", [])

            if not isinstance(events, list):
                return

            for event in events:
                if not isinstance(event, dict):
                    continue

                title = event.get("summary") or event.get("title")
                start = event.get("start")

                if isinstance(start, dict):
                    start = start.get("dateTime") or start.get("date")

                if title:
                    self.extracted_data["meeting_title"] = title

                if start:
                    self.extracted_data["meeting_time"] = start

                attendees = event.get("attendees", [])

                if isinstance(attendees, list):
                    verified_emails = []

                    for attendee in attendees:
                        if isinstance(attendee, dict):
                            email = attendee.get("email")
                            if email:
                                verified_emails.append(email)

                        elif isinstance(attendee, str):
                            verified_emails.append(attendee)

                    self.extracted_data["attendees"] = verified_emails

                # Use the first event returned by the tool.
                break

        # 2. Google Drive extraction
        elif tool_name == "search_files":
            files = data.get("files", [])

            if not isinstance(files, list):
                return

            for file_info in files:
                if not isinstance(file_info, dict):
                    continue

                name = file_info.get("name")
                link = (
                    file_info.get("webViewLink")
                    or file_info.get("webViewUrl")
                    or file_info.get("link")
                )

                if name:
                    self.extracted_data["file_name"] = name

                if link:
                    self.extracted_data["file_link"] = link

                # Use the first file returned by the tool.
                break

        # 3. Gmail draft extraction
        elif tool_name == "create_draft":
            draft_id = data.get("draft_id")

            if draft_id:
                self.extracted_data["draft_id"] = draft_id

    def resolve_tool_args(
        self,
        tool_name: str,
        base_args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolves arguments using actual information collected from tools.

        Does not invent recipients, meeting details, or file information.
        """

        args = dict(base_args)

        if tool_name == "create_draft":
            had_calendar_step = any(
                step.get("tool") == "list_events"
                for step in self.step_outputs
            )

            had_drive_step = any(
                step.get("tool") == "search_files"
                for step in self.step_outputs
            )

            # Enrich the draft only when actual results exist.
            if had_calendar_step or had_drive_step:

                if not args.get("to"):
                    attendees = self.extracted_data.get("attendees", [])

                    if attendees:
                        args["to"] = ", ".join(attendees)

                meeting_title = self.extracted_data.get("meeting_title")
                meeting_time = self.extracted_data.get("meeting_time")
                file_name = self.extracted_data.get("file_name")
                file_link = self.extracted_data.get("file_link")

                if not args.get("subject") and file_name:
                    if meeting_title:
                        args["subject"] = (
                            f"Review Materials: {file_name} "
                            f"for {meeting_title}"
                        )
                    else:
                        args["subject"] = f"Review Materials: {file_name}"

                if not args.get("body"):
                    lines = ["Hello Everyone,", ""]

                    if meeting_title:
                        meeting_details = meeting_title

                        if meeting_time:
                            meeting_details += f" ({meeting_time})"

                        lines.append(
                            f"Ahead of our {meeting_details},"
                        )

                    if file_name:
                        lines.append(
                            f"Here is the document for review: {file_name}"
                        )

                    if file_link:
                        lines.append(f"Document Link: {file_link}")

                    lines.extend([
                        "",
                        "Best regards,",
                        "Personal AI Assistant",
                    ])

                    args["body"] = "\n".join(lines)

        elif tool_name == "send_email":
            # Use only the ID returned by a successful draft operation.
            draft_id = self.extracted_data.get("draft_id")

            if draft_id:
                args["draft_id"] = draft_id

        return args