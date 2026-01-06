from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.auth import (
    get_admin_user,
    get_super_admin_user,
    get_all_users,
    get_user_by_id,
    update_user,
    delete_user,
    create_user,
    create_access_token,
    create_refresh_token,
    users_db,
    ROLE_USER,
    ROLE_ADMIN,
)
from app.routers.shopify import stores_db
from app.routers.products import products_db
from app.routers.tasks import tasks_db

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


# Request/Response models
class CreateClientRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None
    industry: Optional[str] = None
    subscription_tier: str = "free"


class UpdateClientRequest(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    subscription_tier: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class ClientResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    company_name: Optional[str]
    industry: Optional[str]
    role: str
    subscription_tier: str
    is_active: bool
    onboarding_completed: bool
    stores_count: int
    products_count: int
    created_at: str


# Dashboard Stats
@router.get("/dashboard/stats")
async def get_admin_dashboard_stats(
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Get admin dashboard statistics."""
    users = list(users_db.values())
    stores = list(stores_db.values())
    products = list(products_db.values())
    tasks = list(tasks_db.values())

    # Count by subscription tier
    tier_counts = {}
    for user in users:
        tier = user.get("subscription_tier", "free")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Count active vs inactive users
    active_users = len([u for u in users if u.get("is_active", True)])
    inactive_users = len(users) - active_users

    # Count connected stores
    connected_stores = len([s for s in stores if s.get("status") == "connected"])

    return {
        "total_clients": len(users),
        "active_clients": active_users,
        "inactive_clients": inactive_users,
        "total_stores": len(stores),
        "connected_stores": connected_stores,
        "total_products": len(products),
        "total_tasks": len(tasks),
        "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
        "clients_by_tier": tier_counts,
        "recent_signups": len([
            u for u in users
            if u.get("created_at", "")[:10] == datetime.utcnow().isoformat()[:10]
        ]),
    }


# Client Management
@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    search: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """List all clients (users)."""
    users = get_all_users()

    # Apply filters
    if search:
        search_lower = search.lower()
        users = [
            u for u in users
            if search_lower in u.get("email", "").lower()
            or search_lower in (u.get("full_name") or "").lower()
            or search_lower in (u.get("company_name") or "").lower()
        ]

    if subscription_tier:
        users = [u for u in users if u.get("subscription_tier") == subscription_tier]

    if is_active is not None:
        users = [u for u in users if u.get("is_active", True) == is_active]

    # Get store and product counts for each user
    result = []
    for user in users[offset:offset + limit]:
        user_stores = [s for s in stores_db.values() if s.get("user_id") == user["id"]]
        user_store_ids = [s["id"] for s in user_stores]
        user_products = [p for p in products_db.values() if p.get("store_id") in user_store_ids]

        result.append(ClientResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            company_name=user.get("company_name"),
            industry=user.get("industry"),
            role=user.get("role", ROLE_USER),
            subscription_tier=user.get("subscription_tier", "free"),
            is_active=user.get("is_active", True),
            onboarding_completed=user.get("onboarding_completed", False),
            stores_count=len(user_stores),
            products_count=len(user_products),
            created_at=user.get("created_at", ""),
        ))

    return result


@router.get("/clients/{client_id}")
async def get_client(
    client_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Get a specific client with full details."""
    user = get_user_by_id(client_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Get user's stores
    user_stores = [
        {k: v for k, v in s.items() if k != "shopify_access_token"}
        for s in stores_db.values()
        if s.get("user_id") == client_id
    ]

    # Get user's products
    store_ids = [s["id"] for s in user_stores]
    user_products = [
        p for p in products_db.values()
        if p.get("store_id") in store_ids
    ]

    # Get user's tasks
    user_tasks = [
        t for t in tasks_db.values()
        if t.get("store_id") in store_ids
    ]

    return {
        **user,
        "stores": user_stores,
        "products_count": len(user_products),
        "tasks_count": len(user_tasks),
        "pending_tasks": len([t for t in user_tasks if t.get("status") == "pending"]),
    }


@router.post("/clients")
async def create_client(
    request: CreateClientRequest,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Create a new client (user) manually."""
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            company_name=request.company_name,
            industry=request.industry,
            subscription_tier=request.subscription_tier,
        )
        return {k: v for k, v in user.items() if k != "hashed_password"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/clients/{client_id}")
async def update_client(
    client_id: str,
    request: UpdateClientRequest,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Update a client."""
    updates = request.model_dump(exclude_unset=True)
    user = update_user(client_id, updates)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    return user


@router.delete("/clients/{client_id}")
async def deactivate_client(
    client_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Deactivate a client (soft delete)."""
    if not delete_user(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    return {"message": "Client deactivated successfully"}


# Store Management (across all clients)
@router.get("/stores")
async def list_all_stores(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """List all stores across all clients."""
    stores = list(stores_db.values())

    if client_id:
        stores = [s for s in stores if s.get("user_id") == client_id]

    if status:
        stores = [s for s in stores if s.get("status") == status]

    # Add client info to each store
    result = []
    for store in stores[offset:offset + limit]:
        user = get_user_by_id(store.get("user_id", ""))
        result.append({
            **{k: v for k, v in store.items() if k != "shopify_access_token"},
            "client_email": user.get("email") if user else None,
            "client_name": user.get("full_name") if user else None,
        })

    return result


@router.get("/stores/{store_id}")
async def get_store_details(
    store_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Get detailed store information."""
    if store_id not in stores_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )

    store = stores_db[store_id]
    user = get_user_by_id(store.get("user_id", ""))

    # Get store products
    store_products = [p for p in products_db.values() if p.get("store_id") == store_id]

    # Get store tasks
    store_tasks = [t for t in tasks_db.values() if t.get("store_id") == store_id]

    return {
        **{k: v for k, v in store.items() if k != "shopify_access_token"},
        "client": user,
        "products": store_products[:10],  # First 10 products
        "products_count": len(store_products),
        "tasks_count": len(store_tasks),
    }


# Subscription Management
@router.put("/clients/{client_id}/subscription")
async def update_subscription(
    client_id: str,
    subscription_tier: str,
    admin_user: Dict[str, Any] = Depends(get_super_admin_user)
):
    """Update a client's subscription tier."""
    valid_tiers = ["free", "starter", "professional", "enterprise"]
    if subscription_tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )

    user = update_user(client_id, {"subscription_tier": subscription_tier})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    return {
        "message": f"Subscription updated to {subscription_tier}",
        "client": user
    }


# Activity Log (placeholder - would connect to real logging)
@router.get("/activity")
async def get_activity_log(
    client_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Get activity log."""
    # This is a placeholder - in production, this would query an activity log table
    activities = []

    # Generate mock activity from existing data
    for user in list(users_db.values())[:10]:
        activities.append({
            "id": f"activity-{user['id'][:8]}",
            "type": "user_created",
            "description": f"User {user.get('email')} was created",
            "user_id": user["id"],
            "timestamp": user.get("created_at"),
        })

    for store in list(stores_db.values())[:10]:
        activities.append({
            "id": f"activity-{store['id'][:8]}",
            "type": "store_connected",
            "description": f"Store {store.get('shopify_domain')} was connected",
            "store_id": store["id"],
            "timestamp": store.get("created_at"),
        })

    # Sort by timestamp
    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if client_id:
        activities = [a for a in activities if a.get("user_id") == client_id]

    return activities[:limit]


# Masquerade (Login as Client)
@router.post("/masquerade/{client_id}")
async def masquerade_as_client(
    client_id: str,
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Generate tokens to login as a specific client.
    Admin can use this to see exactly what the client sees.
    """
    user = users_db.get(client_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Create tokens for the target user
    access_token = create_access_token(data={"sub": user["id"]})
    refresh_token = create_refresh_token(user["id"])

    # Return user data without sensitive info
    user_data = {k: v for k, v in user.items() if k != "hashed_password"}

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_data,
        "masquerading": True,
        "admin_id": admin_user["id"],
        "admin_email": admin_user["email"],
    }
