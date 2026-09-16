import os
import socket
import services.config # Loads env vars
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
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

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET_KEY environment variable is missing or empty. Please configure JWT_SECRET_KEY in environment variables.")
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


_original_getaddrinfo = socket.getaddrinfo

def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """Force IPv4 DNS resolution for sockets to prevent Errno 101 on cloud platforms without IPv6 routes."""
    try:
        res = _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        if res:
            return res
    except Exception:
        pass
    return _original_getaddrinfo(host, port, family, type, proto, flags)


def _send_via_resend(api_key: str, to_email: str, subject: str, body_text: str, body_html: Optional[str], raise_on_error: bool) -> bool:
    import urllib.request
    import urllib.error
    import json

    resend_from = os.getenv("RESEND_FROM", "").strip()
    if not resend_from:
        resend_from = "Engineering Review <onboarding@resend.dev>"

    payload = {
        "from": resend_from,
        "to": [to_email],
        "subject": subject,
        "text": body_text,
    }
    if body_html:
        payload["html"] = body_html

    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                print(f"[Resend API Success] Sent email to {to_email}")
                return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"[Resend API Error {e.code}]: {err_body}")
        if raise_on_error:
            raise RuntimeError(f"Resend API Error ({e.code}): {err_body}")
    except Exception as e:
        print(f"[Resend API Error]: {e}")
        if raise_on_error:
            raise RuntimeError(f"Resend API email error: {e}")
    return False


def _send_via_brevo(api_key: str, to_email: str, subject: str, body_text: str, body_html: Optional[str], raise_on_error: bool) -> bool:
    import urllib.request
    import json
    sender_email = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "")).strip() or "no-reply@engineeringdrawings.com"
    payload = {
        "sender": {"email": sender_email, "name": "Engineering Review"},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text,
    }
    if body_html:
        payload["htmlContent"] = body_html

    try:
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": api_key,
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                print(f"[Brevo API Success] Sent email to {to_email}")
                return True
    except Exception as e:
        print(f"[Brevo API Error]: {e}")
        if raise_on_error:
            raise RuntimeError(f"Brevo API email error: {e}")
    return False


def send_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None, raise_on_error: bool = False):
    # 1. Try Resend HTTP API if key is configured (HTTPS Port 443 — NEVER blocked by Render)
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    if resend_key:
        print(f"\n--- [EMAIL ATTEMPT] via Resend API to: {to_email} ---")
        return _send_via_resend(resend_key, to_email, subject, body_text, body_html, raise_on_error)

    # 2. Try Brevo HTTP API if key is configured (HTTPS Port 443 — NEVER blocked by Render)
    brevo_key = os.getenv("BREVO_API_KEY", "").strip()
    if brevo_key:
        print(f"\n--- [EMAIL ATTEMPT] via Brevo API to: {to_email} ---")
        return _send_via_brevo(brevo_key, to_email, subject, body_text, body_html, raise_on_error)

    # 3. Fallback to standard SMTP
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip().strip('"').strip("'").replace(" ", "")
    smtp_from = os.getenv("SMTP_FROM", "").strip() or smtp_user or "no-reply@engineeringdrawings.com"

    sender_header = f"Engineering Review <{smtp_from}>" if "<" not in smtp_from else smtp_from
    print(f"\n--- [EMAIL ATTEMPT] to: {to_email} via {smtp_host}:{smtp_port} ---\nSender: {sender_header}\nSubject: {subject}\n-----------------------------------\n")

    if not smtp_host or not smtp_user or not smtp_password:
        msg = f"Missing SMTP credentials on server: host='{smtp_host}', user='{smtp_user}', password_set={bool(smtp_password)}."
        print(f"[Email Warning] {msg}")
        if raise_on_error:
            raise RuntimeError(msg)
        return False

    old_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _ipv4_getaddrinfo

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

        primary_err: Optional[str] = None
        try:
            if smtp_port == 465:
                with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [to_email], msg.as_string())
            print(f"[Email Success] Sent email to {to_email} via {smtp_host}:{smtp_port}")
            return True
        except Exception as e1:
            primary_err = str(e1)
            print(f"[Email Primary Error] Failed on {smtp_host}:{smtp_port}: {e1}")

        # Fallback attempt on port 465 (SSL) if primary was 587, or port 587 if primary was 465
        fallback_port = 465 if smtp_port != 465 else 587
        fallback_err: Optional[str] = None
        print(f"[Email Fallback] Retrying via {smtp_host}:{fallback_port}...")
        try:
            if fallback_port == 465:
                with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(smtp_host, 587, timeout=15) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [to_email], msg.as_string())
            print(f"[Email Fallback Success] Sent email to {to_email} via {smtp_host}:{fallback_port}")
            return True
        except Exception as e2:
            fallback_err = str(e2)
            print(f"[Email Fallback Error] Failed on {smtp_host}:{fallback_port}: {e2}")
            import traceback
            traceback.print_exc()
            if raise_on_error:
                raise RuntimeError(f"SMTP send failed on port {smtp_port} ({primary_err}) and fallback port {fallback_port} ({fallback_err})")
            return False
    finally:
        socket.getaddrinfo = old_getaddrinfo


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
    hashed = hash_password(password)
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = LOWER(%s)", (clean_email,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="User with this email already exists")

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
        print(f"[Google Auth HTTP Error] {url}: {e}")
    return None


def verify_google_id_token(token_str: str) -> Dict[str, Any]:
    """Verify Google OAuth2 ID token or Access token via Google API endpoints."""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()

    # 1. Try ID token verification
    info = _fetch_google_json(f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}")
    if info and info.get("email"):
        aud = info.get("aud")
        if google_client_id and aud and aud != google_client_id:
            print(f"[Google Auth] ID Token client mismatch. aud={aud}, expected={google_client_id}")
        else:
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


def create_email_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
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
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
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
