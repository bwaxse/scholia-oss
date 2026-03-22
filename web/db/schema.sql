-- Scholia Database Schema
-- PostgreSQL database for storing sessions, conversations, and metadata
-- Tables are ordered by dependency (referenced tables come first)

--------------------------------------------------------------------------------
-- USERS
--------------------------------------------------------------------------------

-- Users table: single local user for local-first mode
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    picture TEXT,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed the local user
INSERT INTO users (id, email, name, is_admin)
VALUES ('local-user', 'local@localhost', 'Local User', TRUE)
ON CONFLICT (id) DO NOTHING;

-- User Zotero credentials: per-user Zotero API configuration
CREATE TABLE IF NOT EXISTS user_zotero_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL,
    library_id TEXT NOT NULL,
    library_type TEXT DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Notion credentials: per-user Notion OAuth access tokens
CREATE TABLE IF NOT EXISTS user_notion_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    bot_id TEXT,
    workspace_id TEXT,
    workspace_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

--------------------------------------------------------------------------------
-- PAPER SESSIONS & ANALYSIS
--------------------------------------------------------------------------------

-- Sessions table: stores paper information and PDF location
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    zotero_key TEXT,
    pdf_path TEXT NOT NULL,
    page_count INTEGER,
    file_size_bytes INTEGER,
    label TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete: NULL = active, timestamp = deleted
);

-- Conversations table: stores chat messages between user and Claude
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    highlighted_text TEXT,
    page_number INTEGER,
    model TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete: NULL = visible, timestamp = deleted
);

-- Flags table: user-flagged exchanges for later review
CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Highlights table: text selections user wants to save
CREATE TABLE IF NOT EXISTS highlights (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    page_number INTEGER,
    exchange_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message evaluations: thumbs up/down feedback on AI responses
CREATE TABLE IF NOT EXISTS message_evaluations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative')),
    reason_inaccurate BOOLEAN DEFAULT FALSE,
    reason_unhelpful BOOLEAN DEFAULT FALSE,
    reason_off_topic BOOLEAN DEFAULT FALSE,
    reason_other BOOLEAN DEFAULT FALSE,
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (session_id, exchange_id)
);

CREATE INDEX IF NOT EXISTS idx_evaluations_session ON message_evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_rating ON message_evaluations(rating);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON message_evaluations(created_at DESC);

-- Metadata table: extracted paper metadata
CREATE TABLE IF NOT EXISTS metadata (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT,
    authors TEXT,
    doi TEXT,
    arxiv_id TEXT,
    publication_date TEXT,
    journal TEXT,
    journal_abbr TEXT,
    abstract TEXT
);

-- Insights table: cached extracted insights from conversations
CREATE TABLE IF NOT EXISTS insights (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    insights_json TEXT NOT NULL,
    exchange_count INTEGER NOT NULL,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

--------------------------------------------------------------------------------
-- EXTERNAL INTEGRATIONS
--------------------------------------------------------------------------------

-- Notion project cache: cached project context for faster relevance generation
CREATE TABLE IF NOT EXISTS notion_project_cache (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    page_id TEXT NOT NULL,
    title TEXT NOT NULL,
    hypothesis TEXT,
    themes TEXT,
    raw_content TEXT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, page_id)
);

--------------------------------------------------------------------------------
-- USAGE TRACKING
--------------------------------------------------------------------------------

-- Token usage table: tracks AI API token consumption per call
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    exchange_id INTEGER,
    operation_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    use_thinking BOOLEAN DEFAULT FALSE,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    thinking_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cached_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User events table: tracks user activities
CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

--------------------------------------------------------------------------------
-- INDEXES
--------------------------------------------------------------------------------

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_zotero ON sessions(zotero_key);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_exchange ON conversations(session_id, exchange_id);
CREATE INDEX IF NOT EXISTS idx_conversations_visible ON conversations(session_id, exchange_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_flags_session ON flags(session_id);
CREATE INDEX IF NOT EXISTS idx_highlights_session ON highlights(session_id);

-- Integration indexes
CREATE INDEX IF NOT EXISTS idx_notion_cache_user ON notion_project_cache(user_id);
CREATE INDEX IF NOT EXISTS idx_notion_cache_fetched ON notion_project_cache(user_id, fetched_at DESC);

-- Usage tracking indexes
CREATE INDEX IF NOT EXISTS idx_token_usage_user ON token_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_session ON token_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_created ON token_usage(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_user ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_type ON user_events(event_type);
CREATE INDEX IF NOT EXISTS idx_user_events_created ON user_events(created_at DESC);
