"""
Supabase Server-Side Client Service for PlacementIQ AI.
Provides unified server-side access to Supabase PostgreSQL, Storage, and Realtime.
All operations execute strictly on the backend with zero secret exposure to client JavaScript.
"""
import os
from typing import Optional, Dict, Any


class SupabaseService:
    """Manages server-side Supabase configuration and client interactions."""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "https://oxjxpkwkrtbidvfwfvuq.supabase.co")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self._client = None

    @property
    def is_configured(self) -> bool:
        """Checks if minimum Supabase credentials are provided."""
        return bool(self.supabase_url and (self.service_role_key or self.anon_key))

    def get_headers(self, use_service_role: bool = True) -> Dict[str, str]:
        """Generate authenticated REST API headers for Supabase server-side requests."""
        key = (self.service_role_key or self.anon_key) if use_service_role else (self.anon_key or self.service_role_key)
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def get_public_url(self, bucket: str, path: str) -> str:
        """Constructs public URL for object in Supabase Storage."""
        clean_url = self.supabase_url.rstrip("/")
        return f"{clean_url}/storage/v1/object/public/{bucket}/{path.lstrip('/')}"


_supabase_service = None


def get_supabase_service() -> SupabaseService:
    """Singleton getter for SupabaseService."""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
