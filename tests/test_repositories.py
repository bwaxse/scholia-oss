#!/usr/bin/env python3
"""
Test repository implementations
"""

import sqlite3
import tempfile
from pathlib import Path
import json

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.schema import init_schema
from storage import SQLitePaperRepository, SQLiteSessionRepository, SQLiteCacheRepository


def get_test_db():
    """Create a test database in memory"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def test_paper_repository():
    """Test PaperRepository operations"""
    print("\n" + "=" * 60)
    print("Testing PaperRepository")
    print("=" * 60)

    conn = get_test_db()
    repo = SQLitePaperRepository(conn)

    # Create a paper
    print("\n1. Creating paper...")
    paper_id = repo.create(
        pdf_hash="abc123def456",
        pdf_path="/path/to/paper.pdf",
        title="Attention Is All You Need",
        authors=json.dumps(["Vaswani", "Shazeer", "Parmar"]),
        doi="10.1234/test",
        arxiv_id="1706.03762",
        zotero_key="ABCD1234"
    )
    print(f"✓ Created paper with ID: {paper_id}")

    # Find by ID
    print("\n2. Finding by ID...")
    paper = repo.find_by_id(paper_id)
    assert paper is not None
    assert paper['title'] == "Attention Is All You Need"
    print(f"✓ Found paper: {paper['title']}")

    # Find by hash
    print("\n3. Finding by PDF hash...")
    paper = repo.find_by_hash("abc123def456")
    assert paper is not None
    assert paper['id'] == paper_id
    print(f"✓ Found paper by hash")

    # Find by Zotero key
    print("\n4. Finding by Zotero key...")
    paper = repo.find_by_zotero_key("ABCD1234")
    assert paper is not None
    assert paper['id'] == paper_id
    print(f"✓ Found paper by Zotero key")

    # Find by DOI
    print("\n5. Finding by DOI...")
    paper = repo.find_by_doi("10.1234/test")
    assert paper is not None
    assert paper['id'] == paper_id
    print(f"✓ Found paper by DOI")

    # Update metadata
    print("\n6. Updating metadata...")
    repo.update_metadata(paper_id, {
        'abstract': 'This is a test abstract',
        'journal': 'NeurIPS'
    })
    paper = repo.find_by_id(paper_id)
    assert paper['abstract'] == 'This is a test abstract'
    assert paper['journal'] == 'NeurIPS'
    print(f"✓ Metadata updated")

    # Store PDF chunks
    print("\n7. Storing PDF chunks...")
    chunks = [
        {'chunk_index': 0, 'chunk_type': 'abstract', 'content': 'Abstract text...', 'start_page': 1, 'end_page': 1},
        {'chunk_index': 1, 'chunk_type': 'methods', 'content': 'Methods text...', 'start_page': 2, 'end_page': 4},
    ]
    repo.store_pdf_chunks(paper_id, chunks)
    retrieved_chunks = repo.get_pdf_chunks(paper_id)
    assert len(retrieved_chunks) == 2
    print(f"✓ Stored and retrieved {len(retrieved_chunks)} chunks")

    # Store PDF images
    print("\n8. Storing PDF images...")
    images = [
        {'page_number': 3, 'image_index': 0, 'image_data': b'fake_image_data', 'width': 800, 'height': 600},
    ]
    repo.store_pdf_images(paper_id, images)
    retrieved_images = repo.get_pdf_images(paper_id)
    assert len(retrieved_images) == 1
    print(f"✓ Stored and retrieved {len(retrieved_images)} images")

    # Search
    print("\n9. Searching papers...")
    results = repo.search("Attention")
    assert len(results) == 1
    assert results[0]['id'] == paper_id
    print(f"✓ Search found {len(results)} result(s)")

    # List all
    print("\n10. Listing all papers...")
    all_papers = repo.list_all()
    assert len(all_papers) == 1
    print(f"✓ Listed {len(all_papers)} paper(s)")

    print("\n✅ All PaperRepository tests passed!")


def test_session_repository():
    """Test SessionRepository operations"""
    print("\n" + "=" * 60)
    print("Testing SessionRepository")
    print("=" * 60)

    conn = get_test_db()
    paper_repo = SQLitePaperRepository(conn)
    session_repo = SQLiteSessionRepository(conn)

    # Create a paper first
    paper_id = paper_repo.create(
        pdf_hash="test123",
        title="Test Paper"
    )

    # Create a session
    print("\n1. Creating session...")
    session_id = session_repo.create(paper_id, session_id="test-session-1")
    print(f"✓ Created session: {session_id}")

    # Get session
    print("\n2. Getting session...")
    session = session_repo.get_by_id(session_id)
    assert session is not None
    assert session['paper_id'] == paper_id
    assert session['status'] == 'active'
    print(f"✓ Retrieved session with status: {session['status']}")

    # Add messages
    print("\n3. Adding messages...")
    user_msg_id = session_repo.add_message(session_id, 'user', 'What is this paper about?')
    assistant_msg_id = session_repo.add_message(session_id, 'assistant', 'This paper discusses...')
    print(f"✓ Added 2 messages")

    # Get messages
    print("\n4. Getting messages...")
    messages = session_repo.get_messages(session_id)
    assert len(messages) == 2
    print(f"✓ Retrieved {len(messages)} messages")

    # Get recent messages
    print("\n5. Getting recent messages...")
    recent = session_repo.get_recent_messages(session_id, count=2)
    assert len(recent) == 2
    assert recent[0]['role'] == 'user'  # Chronological order
    assert recent[1]['role'] == 'assistant'
    print(f"✓ Retrieved {len(recent)} recent message(s)")

    # Add flag
    print("\n6. Flagging exchange...")
    flag_id = session_repo.add_flag(session_id, user_msg_id, assistant_msg_id, "Important insight")
    flags = session_repo.get_flags(session_id)
    assert len(flags) == 1
    assert flags[0]['note'] == "Important insight"
    print(f"✓ Flagged exchange with note")

    # Add insights
    print("\n7. Adding insights...")
    session_repo.add_insight(session_id, 'strength', 'Novel architecture', from_flag=True)
    session_repo.add_insight(session_id, 'weakness', 'Limited evaluation')
    insights = session_repo.get_insights(session_id)
    assert len(insights) == 2
    print(f"✓ Added {len(insights)} insights")

    # Add insights bulk
    print("\n8. Adding insights in bulk...")
    insights_data = {
        'methodological_note': ['Uses transformers', 'Self-attention mechanism'],
        'finding': ['Outperforms RNNs']
    }
    count = session_repo.add_insights_bulk(session_id, insights_data)
    assert count == 3
    print(f"✓ Added {count} insights in bulk")

    # Get insights grouped
    print("\n9. Getting insights grouped by category...")
    grouped = session_repo.get_insights_grouped(session_id)
    assert 'strength' in grouped
    assert 'methodological_note' in grouped
    assert len(grouped['methodological_note']) == 2
    print(f"✓ Retrieved insights in {len(grouped)} categories")

    # Get session stats
    print("\n10. Getting session stats...")
    stats = session_repo.get_session_stats(session_id)
    assert stats['total_messages'] == 2
    assert stats['flags'] == 1
    assert stats['insights'] == 5
    print(f"✓ Stats: {stats['total_messages']} messages, {stats['flags']} flags, {stats['insights']} insights")

    # Update status
    print("\n11. Completing session...")
    session_repo.complete_session(session_id)
    session = session_repo.get_by_id(session_id)
    assert session['status'] == 'completed'
    assert session['ended_at'] is not None
    print(f"✓ Session status: {session['status']}")

    # List sessions for paper
    print("\n12. Listing sessions for paper...")
    sessions = session_repo.list_for_paper(paper_id)
    assert len(sessions) == 1
    print(f"✓ Found {len(sessions)} session(s) for paper")

    print("\n✅ All SessionRepository tests passed!")


def test_cache_repository():
    """Test CacheRepository operations"""
    print("\n" + "=" * 60)
    print("Testing CacheRepository")
    print("=" * 60)

    conn = get_test_db()
    repo = SQLiteCacheRepository(conn)

    # Set cache value
    print("\n1. Setting cache value...")
    repo.set('test_key_1', b'test_data_1', 'pdf_text', ttl=3600)
    print("✓ Cached value with 1 hour TTL")

    # Get cache value
    print("\n2. Getting cache value...")
    data = repo.get('test_key_1')
    assert data == b'test_data_1'
    print("✓ Retrieved cached value")

    # Set cache without TTL
    print("\n3. Setting permanent cache...")
    repo.set('test_key_2', b'test_data_2', 'pdf_images', metadata={'pages': 10})
    print("✓ Cached permanent value")

    # Get stats
    print("\n4. Getting cache stats...")
    stats = repo.get_stats()
    assert stats['total_entries'] == 2
    assert stats['total_hits'] == 1  # From first get
    print(f"✓ Stats: {stats['total_entries']} entries, {stats['total_hits']} hits")

    # Get by type
    print("\n5. Getting entries by type...")
    pdf_text_entries = repo.get_by_type('pdf_text')
    assert len(pdf_text_entries) == 1
    print(f"✓ Found {len(pdf_text_entries)} 'pdf_text' entries")

    # Record additional hits
    print("\n6. Recording cache hits...")
    repo.record_hit('test_key_1')
    repo.record_hit('test_key_1')
    stats = repo.get_stats()
    assert stats['total_hits'] == 3
    print(f"✓ Total hits: {stats['total_hits']}")

    # Clear specific type
    print("\n7. Clearing cache by type...")
    deleted = repo.clear('pdf_text')
    assert deleted == 1
    remaining = repo.get_stats()
    assert remaining['total_entries'] == 1
    print(f"✓ Deleted {deleted} entries, {remaining['total_entries']} remaining")

    # Delete specific entry
    print("\n8. Deleting specific entry...")
    deleted = repo.delete('test_key_2')
    assert deleted is True
    print("✓ Deleted entry")

    # Verify empty
    stats = repo.get_stats()
    assert stats['total_entries'] == 0
    print("✓ Cache is empty")

    print("\n✅ All CacheRepository tests passed!")


def test_cascade_delete():
    """Test cascade deletion behavior"""
    print("\n" + "=" * 60)
    print("Testing Cascade Deletion")
    print("=" * 60)

    conn = get_test_db()
    paper_repo = SQLitePaperRepository(conn)
    session_repo = SQLiteSessionRepository(conn)

    # Create paper and session with data
    paper_id = paper_repo.create(pdf_hash="cascade_test", title="Test Paper")
    session_id = session_repo.create(paper_id)
    session_repo.add_message(session_id, 'user', 'Test message')
    session_repo.add_insight(session_id, 'test', 'Test insight')

    print("✓ Created paper with session, messages, and insights")

    # Delete paper
    print("Deleting paper...")
    paper_repo.delete(paper_id)

    # Verify session is also deleted (cascade)
    session = session_repo.get_by_id(session_id)
    assert session is None
    print("✓ Session was cascade-deleted")

    # Verify messages are also deleted
    messages = session_repo.get_messages(session_id)
    assert len(messages) == 0
    print("✓ Messages were cascade-deleted")

    print("\n✅ Cascade deletion test passed!")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("REPOSITORY TESTS")
    print("=" * 60)

    test_paper_repository()
    test_session_repository()
    test_cache_repository()
    test_cascade_delete()

    print("\n" + "=" * 60)
    print("🎉 ALL REPOSITORY TESTS PASSED!")
    print("=" * 60)
