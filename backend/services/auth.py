import os
import socket
import services.config  # Loads env vars
import secrets
import smtplib
import logging
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
import jwt
import bcrypt

logger = logging.getLogger(__name__)

# Patch bcrypt.hashpw for passlib 1.7.4 compatibility with bcrypt >= 4.0.0
_original_bcrypt_hashpw = bcrypt.hashpw
def _safe_bcrypt_hashpw(password: bytes, salt: bytes) -> bytes:
    if isinstance(password, bytes) and len(password) > 72:
        password = password[:72]
    return _original_bcrypt_hashpw(password, salt)
bcrypt.hashpw = _safe_bcrypt_hashpw

from fastapi import Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from model.db import connect

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET_KEY environment variable is missing or empty. Please configure JWT_SECRET_KEY in environment variables.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "24"))

def get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        password = pwd_bytes[:72].decode("utf-8", errors="ignore")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    pwd_bytes = plain_password.encode("utf-8")
    if len(pwd_bytes) > 72:
        plain_password = pwd_bytes[:72].decode("utf-8", errors="ignore")
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------- database user queries

import re

EMAIL_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def validate_email_format(email: str) -> None:
    if not email or not EMAIL_DOMAIN_REGEX.match(email.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email address with a complete domain (e.g. user@gmail.com).",
        )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    clean_email = normalize_email(email)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (clean_email,))
            row = cursor.fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
    return dict(row) if row else None


def create_user(email: str, password: str) -> Dict[str, Any]:
    clean_email = normalize_email(email)
    validate_email_format(clean_email)
    hashed = hash_password(password)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = LOWER(%s)", (clean_email,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email address already exists. Please log in instead.",
                )

            cursor.execute("""
                INSERT INTO users (email, password_hash, email_verified, is_active)
                VALUES (%s, %s, FALSE, TRUE)
                RETURNING user_id
            """, (clean_email, hashed))
            user_id = cursor.fetchone()["user_id"]

    return get_user_by_id(user_id)


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

def _fetch_google_json(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    import urllib.request
    import json
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = resp.read().decode('utf-8')
                return json.loads(data)
    except Exception as e:
        logger.error(f"[Google Auth HTTP Error] {url}: {e}")
    return None


def verify_google_id_token(token_str: str) -> Dict[str, Any]:
    """Verify Google OAuth2 ID token or Access token via Google API endpoints."""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    # 1. Try ID token verification
    info = _fetch_google_json(f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}")
    if info and info.get("email"):
        aud = info.get("aud")
        if google_client_id and aud and aud != google_client_id:
            raise HTTPException(status_code=400, detail="Google authentication failed: Client ID mismatch.")
        email = info.get("email")
        sub = info.get("sub")
        if email and sub:
            return {
                "email": email,
                "google_id": sub,
                "email_verified": str(info.get("email_verified")).lower() == "true",
            }

    # 2. Try Access token verification via tokeninfo
    info = _fetch_google_json(f"https://oauth2.googleapis.com/tokeninfo?access_token={token_str}")
    if info and info.get("email"):
        email = info.get("email")
        sub = info.get("sub") or info.get("user_id")
        return {
            "email": email,
            "google_id": sub or email,
            "email_verified": True,
        }

    # 3. Fallback to UserInfo endpoint
    info = _fetch_google_json("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {token_str}"})
    if info and info.get("email"):
        email = info.get("email")
        sub = info.get("sub")
        if email and sub:
            return {
                "email": email,
                "google_id": sub,
                "email_verified": str(info.get("email_verified")).lower() == "true",
            }

    raise HTTPException(status_code=400, detail="Invalid or expired Google authentication token.")


def get_or_create_google_user(email: str, google_id: str) -> Dict[str, Any]:
    clean_email = normalize_email(email)
    with connect() as conn:
        with conn.cursor() as cursor:
            # Ensure google_id column exists on legacy schemas
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);")
            except Exception:
                pass

            # Check by google_id first
            cursor.execute("SELECT * FROM users WHERE google_id = %s", (google_id,))
            user = cursor.fetchone()
            if user:
                return dict(user)

            # Check by email
            cursor.execute("SELECT * FROM users WHERE email = %s", (clean_email,))
            user_by_email = cursor.fetchone()
            if user_by_email:
                # Link google_id to existing account and verify email
                cursor.execute("""
                    UPDATE users SET google_id = %s, email_verified = TRUE WHERE email = %s
                """, (google_id, clean_email))
                cursor.execute("SELECT * FROM users WHERE email = %s", (clean_email,))
                return dict(cursor.fetchone())

            # Create new Google user
            cursor.execute("""
                INSERT INTO users (email, google_id, email_verified, is_active)
                VALUES (%s, %s, TRUE, TRUE)
                RETURNING user_id
            """, (clean_email, google_id))
            user_id = cursor.fetchone()["user_id"]

    return get_user_by_id(user_id)


def delete_user_account(user_id: int) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            affected = cursor.rowcount
    return affected > 0


# ---------------------------------------------------------------- password reset

def create_password_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_resets (
                    reset_token VARCHAR(255) PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                INSERT INTO password_resets (reset_token, user_id, expires_at, used)
                VALUES (%s, %s, %s, FALSE)
            """, (token, user_id, expires_at))
    return token


def reset_password_with_token(token: str, new_password: str) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM password_resets
                WHERE reset_token = %s AND used = FALSE AND expires_at > NOW()
            """, (token,))
            rec = cursor.fetchone()
            if not rec:
                return False
            new_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, rec["user_id"]))
            cursor.execute("UPDATE password_resets SET used = TRUE WHERE reset_token = %s", (token,))
    return True


# ---------------------------------------------------------------- FastAPI dependency

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = credentials.credentials
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(int(user_id))
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="User account is inactive or disabled")

    return user


def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> Optional[Dict[str, Any]]:
    if not credentials or not credentials.credentials:
        return None
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = get_user_by_id(int(user_id))
        return user if user and user.get("is_active") else None
    except Exception:
        return None


def get_current_user_or_query(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """Require Bearer header authentication (query tokens deprecated for security)."""
    return get_current_user(credentials)
