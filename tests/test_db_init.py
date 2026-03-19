#!/usr/bin/env python3
"""
Test database initialization
"""

import sqlite3
import tempfile
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_db
from db.schema import init_schema, get_current_schema_version, ensure_schema, reset_database


def test_init_schema():
    """Test schema initialization"""
    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)

    try:
        # Get connection to temp database
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        # Initialize schema
        print("Initializing schema...")
        init_schema(conn)

        # Check version
        version = get_current_schema_version(conn)
        print(f"✓ Schema version: {version}")
        assert version == 1, f"Expected version 1, got {version}"

        # Check tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = [
            'cache',
            'flags',
            'insights',
            'messages',
            'papers',
            'pdf_chunks',
            'pdf_images',
            'schema_version',
            'sessions'
        ]

        print(f"✓ Found {len(tables)} tables")
        for table in expected_tables:
            assert table in tables, f"Missing table: {table}"
            print(f"  - {table}")

        # Check indexes exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
        )
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"✓ Found {len(indexes)} indexes")

        # Test idempotency - running again should not error
        print("\nTesting idempotency...")
        init_schema(conn)
        print("✓ Schema initialization is idempotent")

        # Test ensure_schema
        print("\nTesting ensure_schema...")
        ensure_schema(conn)
        print("✓ ensure_schema works")

        # Close connection
        conn.close()

        print("\n✅ All database initialization tests passed!")

    finally:
        # Cleanup
        if db_path.exists():
            db_path.unlink()


def test_basic_operations():
    """Test basic CRUD operations"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        init_schema(conn)

        print("\nTesting basic operations...")

        # Insert a paper
        cursor = conn.execute("""
            INSERT INTO papers (pdf_hash, title, authors)
            VALUES (?, ?, ?)
        """, ('test_hash_123', 'Test Paper', '["Author One", "Author Two"]'))
        paper_id = cursor.lastrowid
        conn.commit()
        print(f"✓ Inserted paper with id={paper_id}")

        # Verify paper exists
        cursor = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        paper = cursor.fetchone()
        assert paper is not None
        assert paper['title'] == 'Test Paper'
        print(f"✓ Retrieved paper: {paper['title']}")

        # Create a session
        cursor = conn.execute("""
            INSERT INTO sessions (id, paper_id, status)
            VALUES (?, ?, ?)
        """, ('test_session_1', paper_id, 'active'))
        conn.commit()
        print("✓ Created session")

        # Add messages
        cursor = conn.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (?, ?, ?)
        """, ('test_session_1', 'user', 'What is this paper about?'))
        user_msg_id = cursor.lastrowid

        cursor = conn.execute("""
            INSERT INTO messages (session_id, role, content)
            VALUES (?, ?, ?)
        """, ('test_session_1', 'assistant', 'This paper discusses...'))
        assistant_msg_id = cursor.lastrowid
        conn.commit()
        print("✓ Added messages")

        # Add a flag
        cursor = conn.execute("""
            INSERT INTO flags (session_id, user_message_id, assistant_message_id, note)
            VALUES (?, ?, ?, ?)
        """, ('test_session_1', user_msg_id, assistant_msg_id, 'Important insight'))
        conn.commit()
        print("✓ Flagged exchange")

        # Verify foreign keys work
        cursor = conn.execute("""
            SELECT f.note, m1.content as user_msg, m2.content as assistant_msg
            FROM flags f
            JOIN messages m1 ON f.user_message_id = m1.id
            JOIN messages m2 ON f.assistant_message_id = m2.id
            WHERE f.session_id = ?
        """, ('test_session_1',))
        flag = cursor.fetchone()
        assert flag is not None
        assert flag['note'] == 'Important insight'
        print(f"✓ Foreign key relationships work")

        # Test cascade delete
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        conn.commit()

        # Verify session was deleted
        cursor = conn.execute("SELECT COUNT(*) FROM sessions WHERE paper_id = ?", (paper_id,))
        count = cursor.fetchone()[0]
        assert count == 0, "Session should be deleted via CASCADE"
        print("✓ CASCADE DELETE works")

        conn.close()

        print("\n✅ All basic operation tests passed!")

    finally:
        if db_path.exists():
            db_path.unlink()


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Database Initialization")
    print("=" * 60)
    test_init_schema()
    test_basic_operations()
    print("\n" + "=" * 60)
    print("🎉 All tests passed!")
    print("=" * 60)
