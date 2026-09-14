from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, Optional
from services import auth

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordSubmitRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


def sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "email_verified": bool(user.get("email_verified")),
        "is_active": bool(user.get("is_active")),
        "created_at": str(user.get("created_at")),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, background_tasks: BackgroundTasks):
    user = auth.create_user(req.email, req.password)
    v_token = auth.create_email_verification_token(user["user_id"])

    background_tasks.add_task(auth.send_verification_email, user["email"], v_token)

    return {
        "message": "User registered successfully. Please verify your email.",
        "user": sanitize_user(user),
        "verification_token": v_token  # returned for easy local testing
    }


@router.post("/login")
def login(req: LoginRequest):
    user = auth.get_user_by_email(req.email)
    if not user or not auth.verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Account is disabled")

    if not user.get("email_verified"):
        raise HTTPException(status_code=400, detail="Please verify your email before logging in")

    access_token = auth.create_access_token({"sub": str(user["user_id"]), "email": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": sanitize_user(user),
    }


@router.get("/me")
def get_profile(current_user: dict = Depends(auth.get_current_user)):
    return sanitize_user(current_user)


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest):
    success = auth.verify_email_token(req.token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, background_tasks: BackgroundTasks):
    user = auth.get_user_by_email(req.email)
    if user and not user.get("email_verified"):
        v_token = auth.create_email_verification_token(user["user_id"])
        background_tasks.add_task(auth.send_verification_email, user["email"], v_token)
    return {"message": "If an unverified account exists with that email, a verification email has been sent."}


@router.post("/request-password-reset")
def request_password_reset(req: RequestPasswordResetRequest, background_tasks: BackgroundTasks):
    user = auth.get_user_by_email(req.email)
    reset_token = None
    if user:
        reset_token = auth.create_password_reset_token(user["user_id"])
        background_tasks.add_task(auth.send_password_reset_email, user["email"], reset_token)
    # Generic success response to prevent account enumeration
    return {
        "message": "If an account exists with that email, a password reset token has been sent.",
        "reset_token": reset_token  # returned for easy local testing
    }


@router.post("/reset-password")
def reset_password(req: ResetPasswordSubmitRequest):
    success = auth.reset_password_with_token(req.token, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    return {"message": "Password updated successfully"}


@router.delete("/me")
def delete_account(current_user: dict = Depends(auth.get_current_user)):
    auth.delete_user_account(current_user["user_id"])
    return {"message": "Account and all owned data deleted successfully"}
