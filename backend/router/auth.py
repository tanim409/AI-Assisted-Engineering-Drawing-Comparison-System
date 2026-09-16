from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Any, Dict, Optional
from services import auth

router = APIRouter()


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
def register(req: RegisterRequest):
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
def google_auth(req: GoogleAuthRequest):
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
        print(f"[Google Auth Error]: {e}")
        raise HTTPException(status_code=400, detail=f"Google authentication failed: {str(e)}")


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
