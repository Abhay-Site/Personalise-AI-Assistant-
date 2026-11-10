"""
tools/gmail.py — Gmail tool implementations

Supports both:
1. Live Google Gmail API (when Google OAuth credentials are provided)
2. Realistic Mock Provider (for offline development and zero-config testing)

All methods:
- Validate input parameters
- Handle exceptions without crashing the agent
- Never log raw email bodies or authorization tokens
"""

import base64
import uuid
from email.message import EmailMessage
from typing import Optional, Any
from app.utils.logging import get_logger

logger = get_logger(__name__)


def is_live_credentials(credentials) -> bool:
    """Returns True only if credentials are real and not the simulated demo token."""
    if not credentials:
        return False
    if getattr(credentials, "token", None) == "mock-access-token-active":
        return False
    if getattr(credentials, "client_id", None) in [None, "", "mock-client-id"]:
        return False
    return True


async def search_emails(query: str, max_results: int = 10, credentials=None) -> dict[str, Any]:
    """Search Gmail messages matching query filter."""
    logger.info(f"Gmail search query='{query}' (max={max_results})")

    if is_live_credentials(credentials):
        try:
            from app.services.google_auth_service import get_gmail_service
            service = get_gmail_service(credentials)
            res = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
            messages = res.get("messages", [])

            results = []
            for m in messages[:max_results]:
                detail = service.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
                snippet = detail.get("snippet", "")
                headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
                results.append({
                    "id": m["id"],
                    "subject": headers.get("subject", "No Subject"),
                    "from": headers.get("from", "Unknown"),
                    "date": headers.get("date", ""),
                    "snippet": snippet,
                })

            return {
                "status": "connected",
                "service": "gmail",
                "query": query,
                "count": len(results),
                "messages": results,
            }
        except Exception as e:
            logger.error(f"Live Gmail search error: {e}")
            return {"status": "error", "message": f"Gmail API error: {str(e)}", "query": query, "messages": []}

    # Realistic Mock Provider for testing/offline mode
    mock_messages = [
        {
            "id": "msg_proj_001",
            "subject": "Project Review Meeting Tomorrow at 2:00 PM",
            "from": "dr.smith@university.edu",
            "date": "Today, 10:15 AM",
            "snippet": "Reminder: Please prepare the latest project report for our review session.",
        },
        {
            "id": "msg_assign_002",
            "subject": "Deep Learning Assignment 2 Due Friday 5:00 PM",
            "from": "ta-cs401@university.edu",
            "date": "Yesterday, 3:30 PM",
            "snippet": "The submission deadline for the backpropagation lab is this Friday at 5 PM.",
        },
    ]

    filtered = [m for m in mock_messages if any(q in m["subject"].lower() or q in m["snippet"].lower() for q in query.lower().split())]
    return {
        "status": "demo",
        "service": "gmail",
        "query": query,
        "count": len(filtered) if filtered else len(mock_messages),
        "messages": filtered if filtered else mock_messages,
    }


async def get_email(email_id: str, credentials=None) -> dict[str, Any]:
    """Retrieve complete content and metadata of a specific email."""
    if is_live_credentials(credentials):
        try:
            from app.services.google_auth_service import get_gmail_service
            service = get_gmail_service(credentials)
            detail = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in detail.get("payload", {}).get("headers", [])}
            return {
                "status": "connected",
                "id": email_id,
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "snippet": detail.get("snippet", ""),
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to retrieve email: {str(e)}"}

    return {
        "status": "demo",
        "id": email_id,
        "subject": "Project Review Meeting Details",
        "from": "dr.smith@university.edu",
        "snippet": "Looking forward to reviewing the Personal AI Assistant architecture and results.",
    }


_PENDING_DRAFTS: dict[str, dict[str, Any]] = {}


async def create_draft(
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    user_id: Optional[int] = None,
    credentials=None,
    **kwargs,
) -> dict[str, Any]:
    """Create a new email draft without sending it. Associates draft with user_id."""
    logger.info(f"Creating email draft: to='{to}', subject='{subject}', user_id={user_id}")

    if is_live_credentials(credentials):
        try:
            from app.services.google_auth_service import get_gmail_service
            service = get_gmail_service(credentials)

            message = EmailMessage()
            message.set_content(body)
            message["To"] = to
            message["Subject"] = subject
            if cc:
                message["Cc"] = cc

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
            real_draft_id = draft.get("id")
            _PENDING_DRAFTS[real_draft_id] = {
                "to": to,
                "subject": subject,
                "body": body,
                "cc": cc,
                "user_id": user_id,
            }

            return {
                "status": "connected",
                "draft_id": real_draft_id,
                "to": to,
                "subject": subject,
                "message": "Draft created in Gmail",
            }
        except Exception as e:
            logger.error(f"Live Gmail create_draft error: {e}")
            return {"status": "error", "message": f"Failed to create draft: {str(e)}"}

    # Unique draft ID per created draft (never hardcoded)
    unique_draft_id = f"draft_{uuid.uuid4().hex[:12]}"
    _PENDING_DRAFTS[unique_draft_id] = {
        "to": to,
        "subject": subject,
        "body": body,
        "cc": cc,
        "user_id": user_id,
    }

    return {
        "status": "demo",
        "draft_id": unique_draft_id,
        "to": to,
        "subject": subject,
        "body_preview": body[:120] + ("..." if len(body) > 120 else ""),
        "message": "Draft prepared in Gmail",
    }


async def send_email(
    draft_id: str,
    user_id: Optional[int] = None,
    credentials=None,
    **kwargs,
) -> dict[str, Any]:
    """
    SENSITIVE: Dispatches an email to recipients.
    Must only be executed after explicit human-in-the-loop approval.
    Requires a valid, existing draft_id belonging to the authenticated user.
    """
    logger.info(f"Sending email draft ID: '{draft_id}' (user_id={user_id})")

    if not draft_id or not isinstance(draft_id, str) or not draft_id.strip():
        logger.warning("send_email called without a valid draft_id")
        return {"status": "error", "message": "A valid non-empty draft_id is required to send an email."}

    draft_id = draft_id.strip()

    # 1. Live Google OAuth API
    if is_live_credentials(credentials):
        try:
            from app.services.google_auth_service import get_gmail_service
            service = get_gmail_service(credentials)
            res = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
            return {
                "status": "connected",
                "sent_message_id": res.get("id"),
                "draft_id": draft_id,
                "message": "Email sent successfully via Gmail API",
            }
        except Exception as e:
            logger.error(f"Live Gmail send_email error: {e}")
            return {"status": "error", "message": f"Failed to send email: {str(e)}"}

    # 2. Validate draft existence and user ownership
    if draft_id not in _PENDING_DRAFTS:
        logger.warning(f"Draft '{draft_id}' not found in pending drafts registry")
        return {
            "status": "error",
            "message": f"Draft '{draft_id}' does not exist or has expired. A valid draft must be created before sending.",
        }

    staged_draft = _PENDING_DRAFTS[draft_id]
    if user_id is not None and staged_draft.get("user_id") is not None:
        if staged_draft["user_id"] != user_id:
            logger.warning(
                f"Unauthorized draft dispatch attempt: user {user_id} tried to send draft {draft_id} owned by {staged_draft['user_id']}"
            )
            return {
                "status": "error",
                "message": f"Unauthorized: Draft '{draft_id}' belongs to another user.",
            }

    # 3. Real SMTP sending (via Gmail App Password)
    try:
        from app.utils.config import get_settings
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        settings = get_settings()
        if settings.smtp_email and settings.smtp_password:
            to_addr = staged_draft.get("to", "team@assistant.dev")
            subj = staged_draft.get("subject", "Message from Personal AI Assistant")
            content = staged_draft.get("body", "Hello from Personal AI Assistant")

            msg = MIMEMultipart()
            msg["From"] = settings.smtp_email
            msg["To"] = to_addr
            msg["Subject"] = subj
            msg.attach(MIMEText(content, "plain"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(settings.smtp_email, settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Real email successfully dispatched via SMTP to {to_addr}")
            return {
                "status": "connected",
                "sent_message_id": "smtp_live_sent",
                "draft_id": draft_id,
                "message": f"Real email dispatched via Gmail SMTP to {to_addr}!",
            }
    except Exception as smtp_err:
        logger.error(f"SMTP dispatch error: {smtp_err}")
        return {"status": "error", "message": f"SMTP Error: {str(smtp_err)}"}

    # 4. Simulated Demo Confirmation
    return {
        "status": "demo",
        "sent_message_id": f"msg_sent_{uuid.uuid4().hex[:8]}",
        "draft_id": draft_id,
        "message": f"Email corresponding to draft '{draft_id}' successfully dispatched (Demo Mode).",
    }
