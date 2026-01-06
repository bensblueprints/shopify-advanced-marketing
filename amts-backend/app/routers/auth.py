from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

from app.services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    users_db,
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    """Register a new user."""
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        access_token = create_access_token(data={"sub": user["id"]})
        refresh_token = create_refresh_token(user["id"])

        # Return user without password
        user_response = {k: v for k, v in user.items() if k != "hashed_password"}

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_response
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return tokens."""
    user = authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(user["id"])

    # Return user without password
    user_response = {k: v for k, v in user.items() if k != "hashed_password"}

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Refresh access token."""
    payload = decode_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id or user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = users_db[user_id]
    access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(user_id)

    user_response = {k: v for k, v in user.items() if k != "hashed_password"}

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=user_response
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return {k: v for k, v in current_user.items() if k != "hashed_password"}


@router.put("/me")
async def update_me(
    updates: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update current user profile."""
    user_id = current_user["id"]

    allowed_fields = ["full_name", "company_name", "industry", "avatar_url", "onboarding_completed"]

    for field in allowed_fields:
        if field in updates:
            users_db[user_id][field] = updates[field]

    return {k: v for k, v in users_db[user_id].items() if k != "hashed_password"}


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate refresh token)."""
    from app.services.auth import refresh_tokens_db
    user_id = current_user["id"]
    if user_id in refresh_tokens_db:
        del refresh_tokens_db[user_id]
    return {"message": "Logged out successfully"}
