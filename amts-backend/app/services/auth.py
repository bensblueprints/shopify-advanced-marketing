from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uuid
import hashlib

from app.config import settings

security = HTTPBearer()

# User roles
ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLE_SUPER_ADMIN = "super_admin"

# In-memory user storage (will be replaced with Supabase)
users_db: Dict[str, Dict[str, Any]] = {}
refresh_tokens_db: Dict[str, str] = {}


def init_admin_user():
    """Initialize the default admin user (Ben)."""
    admin_email = "ben@advancedmarketing.com"

    # Check if admin already exists
    if any(u["email"] == admin_email for u in users_db.values()):
        return

    admin_id = str(uuid.uuid4())
    admin_user = {
        "id": admin_id,
        "email": admin_email,
        "hashed_password": get_password_hash("JEsus777$$!"),  # From CLAUDE.md
        "full_name": "Ben",
        "company_name": "Advanced Marketing",
        "industry": "cannabis",
        "avatar_url": None,
        "role": ROLE_SUPER_ADMIN,
        "subscription_tier": "enterprise",
        "onboarding_completed": True,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    users_db[admin_id] = admin_user
    print(f"Admin user created: {admin_email}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using SHA256 (simple implementation for development)."""
    return get_password_hash(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    """Hash password using SHA256 (simple implementation for development)."""
    # In production, use bcrypt/argon2 with proper configuration
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    refresh_tokens_db[user_id] = encoded_jwt
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
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

    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin or super_admin role."""
    role = current_user.get("role", ROLE_USER)
    if role not in [ROLE_ADMIN, ROLE_SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_super_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require super_admin role."""
    if current_user.get("role") != ROLE_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def create_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = ROLE_USER,
    subscription_tier: str = "free",
    company_name: Optional[str] = None,
    industry: Optional[str] = None,
) -> Dict[str, Any]:
    if any(u["email"] == email for u in users_db.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)

    user = {
        "id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "company_name": company_name,
        "industry": industry,
        "avatar_url": None,
        "role": role,
        "subscription_tier": subscription_tier,
        "onboarding_completed": False,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    users_db[user_id] = user
    return user


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    for user in users_db.values():
        if user["email"] == email:
            if verify_password(password, user["hashed_password"]):
                return user
            return None
    return None


def get_all_users() -> List[Dict[str, Any]]:
    """Get all users (admin only)."""
    return [
        {k: v for k, v in user.items() if k != "hashed_password"}
        for user in users_db.values()
    ]


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID."""
    user = users_db.get(user_id)
    if user:
        return {k: v for k, v in user.items() if k != "hashed_password"}
    return None


def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update user fields."""
    if user_id not in users_db:
        return None

    user = users_db[user_id]

    # Fields that can be updated
    allowed_fields = [
        "full_name", "company_name", "industry", "avatar_url",
        "subscription_tier", "onboarding_completed", "is_active", "role"
    ]

    for field in allowed_fields:
        if field in updates:
            user[field] = updates[field]

    user["updated_at"] = datetime.utcnow().isoformat()
    users_db[user_id] = user

    return {k: v for k, v in user.items() if k != "hashed_password"}


def delete_user(user_id: str) -> bool:
    """Delete a user (soft delete by setting is_active to False)."""
    if user_id not in users_db:
        return False

    users_db[user_id]["is_active"] = False
    users_db[user_id]["updated_at"] = datetime.utcnow().isoformat()
    return True


# Initialize admin user on module load
init_admin_user()
