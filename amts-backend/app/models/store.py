from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class StoreStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class StoreBase(BaseModel):
    name: str
    shopify_domain: str
    industry: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    logo_url: Optional[str] = None


class StoreCreate(StoreBase):
    user_id: str
    shopify_access_token: Optional[str] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    logo_url: Optional[str] = None
    shopify_access_token: Optional[str] = None
    status: Optional[StoreStatus] = None


class Store(StoreBase):
    id: str
    user_id: str
    status: StoreStatus = StoreStatus.PENDING
    shopify_access_token: Optional[str] = None
    products_count: int = 0
    last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoreResponse(BaseModel):
    id: str
    name: str
    shopify_domain: str
    industry: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    logo_url: Optional[str] = None
    status: StoreStatus
    products_count: int
    last_synced: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
