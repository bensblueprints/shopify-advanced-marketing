from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class SubscriptionTier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Subscription(BaseModel):
    id: str
    user_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    ai_generations_used: int = 0
    ai_generations_limit: int = 10  # Free tier default
    products_limit: int = 50  # Free tier default
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    ai_generations_used: int
    ai_generations_limit: int
    products_limit: int

    class Config:
        from_attributes = True


# Subscription tier limits
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "ai_generations": 10,
        "products": 50,
        "stores": 1,
        "price": 0,
    },
    SubscriptionTier.STARTER: {
        "ai_generations": 100,
        "products": 500,
        "stores": 2,
        "price": 4900,  # $49/month in cents
    },
    SubscriptionTier.PROFESSIONAL: {
        "ai_generations": 500,
        "products": 2500,
        "stores": 5,
        "price": 9900,  # $99/month in cents
    },
    SubscriptionTier.ENTERPRISE: {
        "ai_generations": -1,  # Unlimited
        "products": -1,  # Unlimited
        "stores": -1,  # Unlimited
        "price": 29900,  # $299/month in cents
    },
}
