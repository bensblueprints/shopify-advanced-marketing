from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None


class User(UserBase):
    id: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: SubscriptionTier
    onboarding_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True
