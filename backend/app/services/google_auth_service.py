"""
Google OAuth 2.0 and API Client Service.

Credentials and tokens remain on the backend.
"""

import json
from typing import Optional, Any

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from sqlalchemy.orm import Session

from app.database import models
from app.utils.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _build_client_config() -> dict[str, Any]:
    """Build Google OAuth configuration from application settings."""
    settings = get_settings()

    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def get_authorization_url(state: str) -> tuple[str, str]:
    """Create an OAuth URL and save its PKCE verifier."""
    settings = get_settings()

    if not settings.google_oauth_configured:
        raise ValueError(
            "Google OAuth credentials are not configured in backend/.env"
        )

    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.google_redirect_uri,
        autogenerate_code_verifier=True,
    )

    auth_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    from app.utils.oauth_state import save_oauth_state

    save_oauth_state(returned_state, flow.code_verifier)

    return auth_url, returned_state


def exchange_code_for_credentials(
    code: str,
    code_verifier: str,
) -> Credentials:
    """Exchange the authorization code using its original PKCE verifier."""
    settings = get_settings()

    if not settings.google_oauth_configured:
        raise ValueError("Google OAuth credentials are not configured")

    if not code_verifier:
        raise ValueError(
            "Missing PKCE code verifier. Restart Google login."
        )

    flow = Flow.from_client_config(
        _build_client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.google_redirect_uri,
        code_verifier=code_verifier,
    )

    flow.fetch_token(code=code)

    return flow.credentials


def save_user_credentials(
    db: Session,
    user: models.User,
    credentials: Credentials,
) -> None:
    """Store Google credentials in the database."""
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    user.google_credentials_json = json.dumps(token_data)
    db.commit()

    logger.info("Updated Google credentials for user ID %s", user.id)


def get_user_credentials(
    db: Session,
    user: models.User,
) -> Optional[Credentials]:
    """Load credentials and refresh expired access tokens when possible."""
    if not user.google_credentials_json:
        return None

    try:
        data = json.loads(user.google_credentials_json)

        credentials = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get(
                "token_uri",
                "https://oauth2.googleapis.com/token",
            ),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes", GOOGLE_SCOPES),
        )

        if credentials.expired and credentials.refresh_token:
            logger.info(
                "Refreshing expired Google credentials for user %s",
                user.id,
            )

            credentials.refresh(Request())
            save_user_credentials(db, user, credentials)

        return credentials

    except Exception:
        logger.exception(
            "Failed to load or refresh Google credentials for user %s",
            user.id,
        )
        return None


def revoke_user_credentials(
    db: Session,
    user: models.User,
) -> None:
    """Remove stored Google credentials from the user record."""
    user.google_credentials_json = None
    db.commit()

    logger.info("Removed Google credentials for user ID %s", user.id)


def get_gmail_service(credentials: Credentials) -> Resource:
    """Build an authenticated Gmail API service."""
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def get_calendar_service(credentials: Credentials) -> Resource:
    """Build an authenticated Google Calendar API service."""
    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )


def get_drive_service(credentials: Credentials) -> Resource:
    """Build an authenticated Google Drive API service."""
    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )