"""
tools/drive.py — Google Drive tool implementations.

Supports:
1. Live Google Drive API when valid Google OAuth credentials are available.
2. Clearly labeled simulated results for offline development.

IMPORTANT:
Simulated records are not real Google Drive files.
"""

from typing import Any

from app.utils.logging import get_logger
from app.tools.gmail import is_live_credentials

logger = get_logger(__name__)


def _demo_response(
    operation: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a consistently labeled demo response."""
    return {
        "status": "demo",
        "service": "drive",
        "provenance": "simulated",
        "operation": operation,
        "message": message,
        **extra,
    }


def _error_response(
    operation: str,
    message: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a consistently labeled error response."""
    return {
        "status": "error",
        "service": "drive",
        "operation": operation,
        "message": message,
        **extra,
    }


def _get_drive_service(credentials):
    """Create a Google Drive API service using supplied credentials."""
    from app.services.google_auth_service import get_drive_service

    return get_drive_service(credentials)


async def search_files(
    query: str,
    max_results: int = 10,
    credentials=None,
) -> dict[str, Any]:
    """Search Google Drive files by name."""

    query = (query or "").strip()
    max_results = max(1, min(int(max_results), 100))

    logger.info(
        "Drive search query='%s' (max=%s)",
        query,
        max_results,
    )

    if not query:
        return {
            "status": "error",
            "service": "drive",
            "message": "A search query is required.",
            "files": [],
            "count": 0,
        }

    # Search the real Google Drive when live credentials are available.
    if is_live_credentials(credentials):
        try:
            service = _get_drive_service(credentials)

            # Escape single quotes for the Drive query expression.
            safe_query = query.replace("\\", "\\\\").replace("'", "\\'")

            drive_filter = (
                f"name contains '{safe_query}' and trashed = false"
            )

            response = (
                service.files()
                .list(
                    q=drive_filter,
                    pageSize=max_results,
                    orderBy="modifiedTime desc",
                    fields=(
                        "files(id,name,mimeType,modifiedTime,webViewLink)"
                    ),
                )
                .execute()
            )

            files = [
                {
                    "id": file_info.get("id"),
                    "name": file_info.get("name"),
                    "mime_type": file_info.get("mimeType"),
                    "modified_time": file_info.get("modifiedTime"),
                    "link": file_info.get("webViewLink"),
                    "provenance": "google_drive",
                }
                for file_info in response.get("files", [])
            ]

            return {
                "status": "connected",
                "service": "drive",
                "provenance": "google_drive",
                "query": query,
                "count": len(files),
                "files": files,
            }

        except Exception as exc:
            logger.exception("Live Google Drive search failed")

            return _error_response(
                "search_files",
                f"Google Drive search failed: {exc}",
                query=query,
                count=0,
                files=[],
            )

    # Offline demo mode: these are examples, not actual Drive records.
    mock_files = [
        {
            "id": "demo_file_001",
            "name": "ORBIT_180_Project_Report_Final.pdf",
            "mime_type": "application/pdf",
        },
        {
            "id": "demo_file_002",
            "name": "AI_Machine_Learning_Lecture_Notes.pdf",
            "mime_type": "application/pdf",
        },
        {
            "id": "demo_file_003",
            "name": "Backpropagation_Lab_Guide.docx",
            "mime_type": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        },
    ]

    search_terms = query.lower().split()

    matching_files = [
        {
            **file_info,
            "modified_time": None,
            "link": None,
            "provenance": "simulated",
        }
        for file_info in mock_files
        if all(
            term in file_info["name"].lower()
            for term in search_terms
        )
    ][:max_results]

    return _demo_response(
        "search_files",
        (
            "These are simulated example records, not files retrieved "
            "from Google Drive."
        ),
        query=query,
        count=len(matching_files),
        files=matching_files,
    )


async def get_file_metadata(
    file_id: str,
    credentials=None,
) -> dict[str, Any]:
    """Retrieve metadata for a real Google Drive file."""

    file_id = (file_id or "").strip()

    if not file_id:
        return _error_response(
            "get_file_metadata",
            "A file ID is required.",
            metadata=None,
        )

    if not is_live_credentials(credentials):
        return _demo_response(
            "get_file_metadata",
            (
                "Google Drive is not connected. No real file metadata "
                "was retrieved."
            ),
            file_id=file_id,
            metadata=None,
        )

    try:
        service = _get_drive_service(credentials)

        metadata = (
            service.files()
            .get(
                fileId=file_id,
                fields=(
                    "id,name,mimeType,modifiedTime,webViewLink,size"
                ),
            )
            .execute()
        )

        return {
            "status": "connected",
            "service": "drive",
            "provenance": "google_drive",
            "file_id": file_id,
            "metadata": metadata,
        }

    except Exception as exc:
        logger.exception("Google Drive metadata retrieval failed")

        return _error_response(
            "get_file_metadata",
            f"Google Drive metadata retrieval failed: {exc}",
            file_id=file_id,
            metadata=None,
        )


async def get_file_content(
    file_id: str,
    credentials=None,
) -> dict[str, Any]:
    """
    Retrieve text content from a supported Google Drive document.

    Google Docs documents can be exported as plain text.
    Other file types return an explanatory message rather than
    fabricated document content.
    """

    file_id = (file_id or "").strip()

    if not file_id:
        return _error_response(
            "get_file_content",
            "A file ID is required.",
            content=None,
        )

    if not is_live_credentials(credentials):
        return _demo_response(
            "get_file_content",
            (
                "Google Drive is not connected. No real document "
                "content was retrieved."
            ),
            file_id=file_id,
            content=None,
        )

    try:
        service = _get_drive_service(credentials)

        file_info = (
            service.files()
            .get(
                fileId=file_id,
                fields="id,name,mimeType",
            )
            .execute()
        )

        mime_type = file_info.get("mimeType", "")
        file_name = file_info.get("name")

        # Export Google Docs as plain text.
        if mime_type == "application/vnd.google-apps.document":
            content = (
                service.files()
                .export(
                    fileId=file_id,
                    mimeType="text/plain",
                )
                .execute()
            )

            if isinstance(content, bytes):
                content = content.decode(
                    "utf-8",
                    errors="replace",
                )

            return {
                "status": "connected",
                "service": "drive",
                "provenance": "google_drive",
                "file_id": file_id,
                "name": file_name,
                "mime_type": mime_type,
                "content": content,
            }

        return {
            "status": "connected",
            "service": "drive",
            "provenance": "google_drive",
            "file_id": file_id,
            "name": file_name,
            "mime_type": mime_type,
            "content": None,
            "message": (
                "The file metadata was retrieved successfully, but "
                "automatic content extraction is not implemented "
                "for this file type."
            ),
        }

    except Exception as exc:
        logger.exception("Google Drive content retrieval failed")

        return _error_response(
            "get_file_content",
            f"Google Drive content retrieval failed: {exc}",
            file_id=file_id,
            content=None,
        )