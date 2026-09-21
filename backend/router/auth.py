import logging
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Dict, Optional
from services import auth

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory sliding window rate limiter for auth endpoints
_auth_attempts: Dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60.0  # seconds
MAX_AUTH_ATTEMPTS = 15    # max attempts per window per IP


def enforce_auth_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    
    # Filter attempts within the current window
    attempts = [t for t in _auth_attempts[client_ip] if t > cutoff]
    attempts.append(now)
    _auth_attempts[client_ip] = attempts
    
    if len(attempts) > MAX_AUTH_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait a minute before trying again.",
            headers={"Retry-After": "60"},
        )


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

    @field_validator("email", mode="after")
    @classmethod
    def validate_email_tld(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", str(v).strip()):
            raise ValueError("Please enter a valid email address with a complete domain (e.g. user@gmail.com).")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "email_verified": bool(user.get("email_verified", True)),
        "is_active": bool(user.get("is_active", True)),
        "created_at": str(user.get("created_at")),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, request: Request):
    enforce_auth_rate_limit(request)
    user = auth.create_user(req.email, req.password)
    access_token = auth.create_access_token({"sub": str(user["user_id"]), "email": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": sanitize_user(user),
    }


class GoogleAuthRequest(BaseModel):
    id_token: str


@router.post("/google")
def google_auth(req: GoogleAuthRequest, request: Request):
    enforce_auth_rate_limit(request)
    try:
        g_info = auth.verify_google_id_token(req.id_token)
        user = auth.get_or_create_google_user(g_info["email"], g_info["google_id"])

        if not user.get("is_active"):
            raise HTTPException(status_code=400, detail="Account is disabled")

        access_token = auth.create_access_token({"sub": str(user["user_id"]), "email": user["email"]})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": sanitize_user(user),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Google Auth Error]: {e}")
        raise HTTPException(status_code=400, detail="Google authentication failed. Please check your credentials.")


@router.post("/login")
def login(req: LoginRequest, request: Request):
    enforce_auth_rate_limit(request)
    user = auth.get_user_by_email(req.email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Account is disabled")

    access_token = auth.create_access_token({"sub": str(user["user_id"]), "email": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": sanitize_user(user),
    }


@router.get("/me")
def get_profile(current_user: dict = Depends(auth.get_current_user)):
    return sanitize_user(current_user)


@router.delete("/me")
def delete_account(current_user: dict = Depends(auth.get_current_user)):
    auth.delete_user_account(current_user["user_id"])
    return {"message": "Account and all owned data deleted successfully"}


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


@router.post("/request-password-reset")
def request_password_reset(req: RequestPasswordResetRequest, request: Request):
    enforce_auth_rate_limit(request)
    user = auth.get_user_by_email(req.email)
    if user:
        token = auth.create_password_reset_token(user["user_id"])
        logger.info(f"Password reset token for {req.email}: {token}")
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    success = auth.reset_password_with_token(req.token, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"message": "Password has been reset successfully"}
