"""
api/auth.py — Authentication and Google OAuth 2.0 endpoints

Security principles:
- Access tokens and Refresh tokens NEVER leave the backend.
- The frontend only communicates with FastAPI session / user state.
- Scopes are minimal and transparent.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import crud, models
from app.utils.oauth_state import consume_oauth_state
from app.services.google_auth_service import (
    get_authorization_url,
    exchange_code_for_credentials,
    save_user_credentials,
    get_user_credentials,
    revoke_user_credentials,
)
from app.utils.config import get_settings
from app.utils.security import generate_session_token
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Demo / Local Mock User
MOCK_USER_ID = "mock-google-id-12345"
MOCK_USER_EMAIL = "demo@orbit180.dev"
MOCK_USER_NAME = "Demo User"


def get_mock_user(db: Session = Depends(get_db)) -> models.User:
    """Returns or creates the local active user session."""
    user = crud.get_or_create_user(
        db,
        google_id=MOCK_USER_ID,
        name=MOCK_USER_NAME,
        email=MOCK_USER_EMAIL,
        profile_picture=None,
    )
    return user


@router.get("/login")
def login(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Initiates the Google OAuth 2.0 flow."""
    settings = get_settings()

    if not settings.google_oauth_configured:
        logger.warning("Google OAuth credentials not configured in backend/.env")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?oauth_missing=true"
        )

    try:
        state = generate_session_token()
        auth_url, _ = get_authorization_url(state=state)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.exception("Failed to initiate Google OAuth")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?error=oauth_start_failed"
        )


@router.post("/simulate-connect")
def simulate_connect(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Simulates a connected Google account for offline demo testing."""
    from app.services.google_auth_service import GOOGLE_SCOPES

    mock_token = {
        "token": "mock-access-token-active",
        "refresh_token": "mock-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "mock-client-id",
        "client_secret": "mock-client-secret",
        "scopes": GOOGLE_SCOPES,
    }

    current_user.google_credentials_json = json.dumps(mock_token)
    db.commit()

    logger.info("Simulated Google account enabled for user %s", current_user.id)

    return {
        "status": "demo_connected",
        "mode": "demo",
        "google_connected": False,
        "simulated_connected": True,
        "message": (
            "Simulated Google account connected for local demo mode. "
            "Real Google Cloud APIs require OAuth keys in backend/.env."
        ),
    }


@router.get("/callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """
    Google OAuth 2.0 callback endpoint.
    Exchanges the authorization code and saves credentials.
    """
    settings = get_settings()

    try:
        code_verifier = consume_oauth_state(state)

        if not code_verifier:
            logger.error("OAuth callback failed: missing or expired PKCE verifier")
            return RedirectResponse(
                url=f"{settings.frontend_url}/settings?error=oauth_state_expired"
            )

        credentials = exchange_code_for_credentials(
            code=code,
            code_verifier=code_verifier,
        )

        save_user_credentials(db, current_user, credentials)

        logger.info(
            "Google OAuth connection successful for user %s",
            current_user.email,
        )

        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?connected=true"
        )

    except Exception:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?error=oauth_callback_failed"
        )


@router.get("/me")
def get_current_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Returns the local user profile and connection status."""
    from app.tools.gmail import is_live_credentials

    creds = get_user_credentials(db, current_user)
    is_real_google = is_live_credentials(creds)
    is_simulated = creds is not None and not is_real_google

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "profile_picture": current_user.profile_picture,
        "google_connected": is_real_google,
        "simulated_connected": is_simulated,
        "services": {
            "gmail": is_real_google,
            "calendar": is_real_google,
            "drive": is_real_google,
        },
        "mode": "live" if is_real_google else "demo",
    }


@router.get("/status")
def auth_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Returns OAuth configuration and connection status."""
    from app.tools.gmail import is_live_credentials

    settings = get_settings()
    creds = get_user_credentials(db, current_user)

    is_real_google = is_live_credentials(creds)
    is_simulated = creds is not None and not is_real_google

    missing_keys = []

    if not settings.google_client_id:
        missing_keys.append("GOOGLE_CLIENT_ID")

    if not settings.google_client_secret:
        missing_keys.append("GOOGLE_CLIENT_SECRET")

    return {
        "google_oauth_configured": settings.google_oauth_configured,
        "gemini_configured": settings.gemini_configured,
        "google_connected": is_real_google,
        "simulated_connected": is_simulated,
        "mock_mode": not is_real_google,
        "mode": "live" if is_real_google else "demo",
        "missing_config": missing_keys,
        "oauth_redirect_uri": settings.google_redirect_uri,
    }


@router.post("/disconnect")
def disconnect_google(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Disconnects and revokes Google credentials."""
    revoke_user_credentials(db, current_user)

    return {
        "status": "disconnected",
        "message": "Google account successfully unlinked.",
    }


class ProfileUpdateRequest(BaseModel):
    name: str
    email: str


@router.post("/profile")
def update_profile(
    data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_mock_user),
):
    """Updates the local user profile."""
    if data.name:
        current_user.name = data.name.strip()

    if data.email:
        current_user.email = data.email.strip()

    db.commit()

    logger.info(
        "User profile updated: %s <%s>",
        current_user.name,
        current_user.email,
    )

    return {
        "status": "success",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
    }