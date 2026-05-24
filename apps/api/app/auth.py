"""Clerk JWT verification for FastAPI.

Verifies Clerk-issued JWTs against Clerk's JWKS endpoint and resolves them to
the local User row, auto-upserting on first sign-in by clerk_user_id.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User


class AuthError(Exception):
    pass


_JWKS_CACHE: Dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600


def _get_jwks_url() -> str:
    url = os.getenv("CLERK_JWKS_URL", "").strip()
    if not url:
        raise AuthError(
            "CLERK_JWKS_URL env var is required "
            "(e.g. https://<your-instance>.clerk.accounts.dev/.well-known/jwks.json)"
        )
    return url


def _get_issuer() -> str:
    issuer = os.getenv("CLERK_JWT_ISSUER", "").strip()
    if not issuer:
        raise AuthError(
            "CLERK_JWT_ISSUER env var is required "
            "(e.g. https://<your-instance>.clerk.accounts.dev)"
        )
    return issuer


def _fetch_jwks() -> Dict[str, Any]:
    now = time.time()
    cached = _JWKS_CACHE.get("keys")
    if cached is not None and now - _JWKS_CACHE.get("fetched_at", 0) < _JWKS_TTL_SECONDS:
        return cached
    resp = httpx.get(_get_jwks_url(), timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()
    _JWKS_CACHE["keys"] = jwks
    _JWKS_CACHE["fetched_at"] = now
    return jwks


def _public_key_for_token(token: str):
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise AuthError("JWT missing 'kid' header")
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    # Force one refresh in case the key rotated.
    _JWKS_CACHE["fetched_at"] = 0
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)
    raise AuthError(f"No JWKS key found for kid={kid}")


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a Clerk JWT and return its claims. Raises AuthError on failure."""
    if not token:
        raise AuthError("Empty token")
    try:
        public_key = _public_key_for_token(token)
        claims = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=_get_issuer(),
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise AuthError("Invalid issuer") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"Invalid token: {exc}") from exc
    return claims


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return header.split(" ", 1)[1].strip()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency. Returns the local User row for the authenticated Clerk user.

    Auto-creates a User on first sign-in keyed by clerk_user_id. Email is taken
    from the JWT 'email' claim if present.
    """
    token = _extract_bearer(request)
    try:
        claims = verify_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT missing 'sub' claim",
        )

    user: Optional[User] = (
        db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    )
    if user is None:
        email = claims.get("email")
        user = User(clerk_user_id=clerk_user_id, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
