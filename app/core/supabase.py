"""
Supabase Client Configuration

Provides a singleton Supabase client instance for database operations.
"""

import logging
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton Supabase client
_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance (singleton pattern).

    Returns:
        Configured Supabase client

    Raises:
        ValueError: If Supabase credentials are not configured
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    # Validate configuration
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL not configured in environment")

    if not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not configured in environment")

    # Create client
    _supabase_client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_KEY
    )

    logger.info(f"Supabase client initialized: {settings.SUPABASE_URL}")

    return _supabase_client
