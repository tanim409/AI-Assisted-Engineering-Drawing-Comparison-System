import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
import jwt
import bcrypt

# Patch bcrypt.hashpw for passlib 1.7.4 compatibility with bcrypt >= 4.0.0
# Prevents ValueError when secrets/passwords exceeding 72 bytes are processed by passlib's bug detection
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

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "eng-drawing-jwt-secret-key-change-in-prod-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_HOURS", "24"))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@engineeringdrawings.com")


# ---------------------------------------------------------------- password helpers

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------- JWT helpers

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def send_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None):
    sender_header = f"Engineering Review <{SMTP_FROM}>" if "<" not in SMTP_FROM else SMTP_FROM
    print(f"\n--- [EMAIL SENT] to: {to_email} ---\nSender: {sender_header}\nSubject: {subject}\n{body_text}\n-----------------------------------\n")
    if SMTP_HOST and SMTP_USER:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_header
            msg["To"] = to_email

            part_text = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part_text)

            if body_html:
                part_html = MIMEText(body_html, "html", "utf-8")
                msg.attach(part_html)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        except Exception as e:
            print(f"[Email Error] Failed to send email via SMTP: {e}")


def _build_email_html(title: str, preheader: str, body_html: str, cta_label: str, cta_url: str, footer_note: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #FAFAFA; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #0A0A0A; -webkit-font-smoothing: antialiased;">
  <div style="display: none; max-height: 0px; overflow: hidden;">{preheader}</div>
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #FAFAFA; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #FFFFFF; border: 1px solid #E5E5E5; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);">
          <!-- Header -->
          <tr>
            <td style="padding: 32px 32px 24px 32px; border-bottom: 1px solid #F5F5F5;">
              <table border="0" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="width: 32px; height: 32px; background-color: #0A0A0A; border-radius: 8px; text-align: center; vertical-align: middle; color: #FFFFFF; font-weight: bold; font-size: 16px; font-family: monospace;">Δ</td>
                  <td style="padding-left: 12px; font-size: 16px; font-weight: 700; color: #0A0A0A; letter-spacing: -0.3px;">Engineering Review</td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Main Content -->
          <tr>
            <td style="padding: 32px;">
              <h1 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 700; color: #0A0A0A; letter-spacing: -0.4px;">{title}</h1>
              <div style="font-size: 15px; line-height: 1.6; color: #525252; margin-bottom: 28px;">
                {body_html}
              </div>
              <!-- CTA Button -->
              <table border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                <tr>
                  <td align="center" style="border-radius: 9999px; background-color: #0A0A0A;">
                    <a href="{cta_url}" target="_blank" style="font-size: 14px; font-weight: 600; color: #FFFFFF; text-decoration: none; display: inline-block; padding: 12px 28px; border-radius: 9999px; background-color: #0A0A0A;">{cta_label}</a>
                  </td>
                </tr>
              </table>
              <!-- Plain text fallback link -->
              <div style="padding: 16px; background-color: #FAFAFA; border: 1px solid #E5E5E5; border-radius: 8px; font-size: 12px; color: #737373; line-height: 1.5; word-break: break-all;">
                If the button above doesn't work, copy and paste this link into your browser:<br>
                <a href="{cta_url}" style="color: #0A0A0A; text-decoration: underline;">{cta_url}</a>
              </div>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 24px 32px; background-color: #FAFAFA; border-top: 1px solid #F5F5F5; font-size: 12px; color: #A3A3A3; line-height: 1.5; text-align: center;">
              {footer_note}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_verification_email(to_email: str, token: str):
    frontend_url = get_frontend_url()
    verify_url = f"{frontend_url}/verify-email?token={token}"
    subject = "Verify your email address - Engineering Review"
    body_text = f"Welcome to Engineering Review! Please verify your email by opening this link: {verify_url}"
    html = _build_email_html(
        title="Verify your email address",
        preheader="Please confirm your email address to activate your account.",
        body_html="Thanks for signing up! Click the button below to verify your email address and activate your account.",
        cta_label="Verify Email",
        cta_url=verify_url,
        footer_note="If you didn't create an account with Engineering Review, you can safely ignore this email.",
    )
    send_email(to_email, subject, body_text, html)


def send_password_reset_email(to_email: str, token: str):
    frontend_url = get_frontend_url()
    reset_url = f"{frontend_url}/reset-password?token={token}"
    subject = "Reset your password - Engineering Review"
    body_text = f"We received a request to reset your password. Reset your password here: {reset_url}"
    html = _build_email_html(
        title="Reset your password",
        preheader="Reset your Engineering Review account password.",
        body_html="We received a request to reset the password for your account. Click the button below to choose a new password.",
        cta_label="Reset Password",
        cta_url=reset_url,
        footer_note="If you didn't request a password reset, you can safely ignore this email.",
    )
    send_email(to_email, subject, body_text, html)


# ---------------------------------------------------------------- database user queries

def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    clean_email = normalize_email(email)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (clean_email,))
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
    hashed = hash_password(password)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (clean_email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="User with this email already exists")

            cursor.execute("""
                INSERT INTO users (email, password_hash, email_verified, is_active)
                VALUES (%s, %s, FALSE, TRUE)
            """, (clean_email, hashed))
            user_id = cursor.lastrowid

    return get_user_by_id(user_id)


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """Verify Google OAuth2 ID token via Google's tokeninfo API endpoint."""
    import requests
    try:
        resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token_str}",
            timeout=10
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google authentication token")
        
        info = resp.json()
        # Verify audience if GOOGLE_CLIENT_ID is set
        if GOOGLE_CLIENT_ID and info.get("aud") != GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Google token client ID mismatch")
        
        email = info.get("email")
        google_sub = info.get("sub")
        if not email or not google_sub:
            raise HTTPException(status_code=401, detail="Google token missing required profile info")
        
        return {
            "email": email,
            "google_id": google_sub,
            "email_verified": info.get("email_verified") == "true" or info.get("email_verified") is True,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google token verification failed: {str(e)}")


def get_or_create_google_user(email: str, google_id: str) -> Dict[str, Any]:
    clean_email = normalize_email(email)
    with connect() as conn:
        with conn.cursor() as cursor:
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
            """, (clean_email, google_id))
            user_id = cursor.lastrowid

    return get_user_by_id(user_id)


def create_email_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=24)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO email_verifications (verification_token, user_id, expires_at, used)
                VALUES (%s, %s, %s, FALSE)
            """, (token, user_id, expires_at))
    return token


def verify_email_token(token: str) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM email_verifications
                WHERE verification_token = %s AND used = FALSE AND expires_at > NOW()
            """, (token,))
            rec = cursor.fetchone()
            if not rec:
                return False

            cursor.execute("UPDATE users SET email_verified = TRUE WHERE user_id = %s", (rec["user_id"],))
            cursor.execute("UPDATE email_verifications SET used = TRUE WHERE verification_token = %s", (token,))
    return True


def create_password_reset_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=2)
    with connect() as conn:
        with conn.cursor() as cursor:
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


def delete_user_account(user_id: int) -> bool:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            affected = cursor.rowcount
    return affected > 0


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


def get_current_user_or_query(
    request: Request,
    token: Optional[str] = Query(None),
) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization")
    raw_token = None
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(raw_token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_id(int(user_id))
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=401, detail="User account is inactive or disabled")

    return user
