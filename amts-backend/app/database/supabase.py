from supabase import create_client, Client
from typing import Optional
from app.config import settings

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get Supabase client instance."""
    global _supabase_client

    if _supabase_client is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise ValueError("Supabase URL and Key must be configured")
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )

    return _supabase_client


def get_supabase_admin() -> Client:
    """Get Supabase client with service role key for admin operations."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase URL and Service Key must be configured")

    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )
