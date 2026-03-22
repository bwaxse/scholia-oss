"""
Database connection management for Paper Companion.
Provides async PostgreSQL connection with schema initialization and transaction support.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional, Any

import asyncpg

from .config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages async PostgreSQL database connections.

    Features:
    - Connection pooling for efficient resource usage
    - Automatic schema initialization
    - Transaction context managers
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection string. If None, uses settings.
        """
        self._database_url = database_url or get_settings().database_url
        self._pool: Optional[asyncpg.Pool] = None
        self._lock = asyncio.Lock()

    @property
    def database_url(self) -> str:
        """Get database connection URL."""
        return self._database_url

    async def initialize(self) -> None:
        """
        Initialize database with schema.
        Creates connection pool and tables/indexes if they don't exist.
        """
        # Create connection pool
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )

        # Read schema file
        schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        schema_sql = schema_path.read_text()

        async with self._pool.acquire() as conn:
            # Run migrations FIRST (before schema)
            migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
            if migrations_dir.exists():
                migration_files = sorted(migrations_dir.glob("*.sql"))
                for migration_file in migration_files:
                    migration_sql = migration_file.read_text()
                    try:
                        await conn.execute(migration_sql)
                        logger.info(f"Applied migration: {migration_file.name}")
                    except Exception as e:
                        # Rollback any aborted transaction before continuing
                        try:
                            await conn.execute("ROLLBACK")
                        except Exception:
                            pass
                        logger.warning(f"Migration {migration_file.name} skipped or failed: {e}")

            # Execute schema (after migrations)
            await conn.execute(schema_sql)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Get a database connection from the pool.

        Yields:
            asyncpg.Connection: Database connection

        Example:
            async with db_manager.get_connection() as conn:
                rows = await conn.fetch("SELECT * FROM sessions")
        """
        if self._pool is None:
            await self.initialize()

        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """
        Transaction context manager with automatic commit/rollback.

        Yields:
            asyncpg.Connection: Database connection in transaction

        Example:
            async with db_manager.transaction() as conn:
                await conn.execute("INSERT INTO sessions ...")
                await conn.execute("INSERT INTO metadata ...")
                # Auto-commits on success, rolls back on exception
        """
        async with self.get_connection() as conn:
            async with conn.transaction():
                yield conn

    async def execute_query(
        self,
        query: str,
        *args: Any
    ) -> list[asyncpg.Record]:
        """
        Execute a SELECT query and return all rows.

        Args:
            query: SQL SELECT query (use $1, $2, etc. for parameters)
            *args: Query parameters

        Returns:
            List of rows as Record objects (dict-like access)
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return rows

    async def execute_one(
        self,
        query: str,
        *args: Any
    ) -> Optional[asyncpg.Record]:
        """
        Execute a SELECT query and return first row.

        Args:
            query: SQL SELECT query
            *args: Query parameters

        Returns:
            First row as Record object, or None if no results
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return row

    async def execute_insert(
        self,
        query: str,
        *args: Any
    ) -> Optional[Any]:
        """
        Execute an INSERT query and return the result.

        For RETURNING clauses, returns the specified value.
        For simple inserts, returns None.

        Args:
            query: SQL INSERT query (add RETURNING id for auto-generated IDs)
            *args: Query parameters

        Returns:
            Value from RETURNING clause, or None
        """
        async with self.transaction() as conn:
            result = await conn.fetchval(query, *args)
            return result

    async def execute_update(
        self,
        query: str,
        *args: Any
    ) -> str:
        """
        Execute an UPDATE/DELETE query and return status.

        Args:
            query: SQL UPDATE/DELETE query
            *args: Query parameters

        Returns:
            Status string (e.g., "UPDATE 1", "DELETE 3")
        """
        async with self.transaction() as conn:
            result = await conn.execute(query, *args)
            return result

    async def health_check(self) -> bool:
        """
        Verify database is accessible and functional.

        Returns:
            True if database is healthy
        """
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance (singleton pattern).

    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def init_database() -> None:
    """
    Initialize database with schema.
    Should be called during application startup.
    """
    db_manager = get_db_manager()
    await db_manager.initialize()


# Convenience function for FastAPI dependency injection
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency for getting database connection.

    Usage:
        @app.get("/sessions")
        async def list_sessions(db: asyncpg.Connection = Depends(get_db)):
            rows = await db.fetch("SELECT * FROM sessions")
            return rows
    """
    db_manager = get_db_manager()
    async with db_manager.get_connection() as conn:
        yield conn
