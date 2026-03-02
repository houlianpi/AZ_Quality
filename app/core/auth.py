"""Authentication module for Azure AD integration."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWKClient
from typing import Any

from app.core.config import settings

security = HTTPBearer()


class AuthError(Exception):
    """Authentication error."""
    pass


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """
    Validate Azure AD token and extract user information.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        User information from token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Get signing keys from Azure AD
        jwks_uri = f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/discovery/v2.0/keys"
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.AAD_CLIENT_ID,
            issuer=f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/v2.0",
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
        )


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify AAD JWT token and return user claims.
    Standalone function for testing.
    """
    if not settings.AAD_CLIENT_ID or not settings.AAD_TENANT_ID:
        raise AuthError("AAD not configured")

    try:
        jwks_uri = f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/discovery/v2.0/keys"
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.AAD_CLIENT_ID,
            issuer=f"https://login.microsoftonline.com/{settings.AAD_TENANT_ID}/v2.0",
        )

        return payload
    except Exception as e:
        raise AuthError(f"Token verification failed: {e}")
