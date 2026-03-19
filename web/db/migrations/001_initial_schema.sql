-- Migration 001: Initial Schema
-- Scholia Database Schema - Pre-Production Baseline
-- PostgreSQL database for storing sessions, conversations, metadata, and billing
--
-- This is a consolidated baseline representing the complete schema at pre-production launch.
-- All tables are ordered by dependency (referenced tables come first).
--
-- NOTE: This schema already includes the 20× credit multiplier refactor
-- (monthly_credits, credit_transactions, etc. use INTEGER instead of NUMERIC)

BEGIN;

--------------------------------------------------------------------------------
-- USERS & AUTH
--------------------------------------------------------------------------------

-- Users table: authenticated users from OAuth (Google, GitHub, etc.)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,  -- UUID
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    picture TEXT,  -- Profile picture URL
    is_admin BOOLEAN DEFAULT FALSE,  -- Admin users have access to advanced features
    is_banned BOOLEAN DEFAULT FALSE,  -- Whether user is banned
    banned_at TIMESTAMPTZ,  -- When user was banned
    ban_reason TEXT,  -- Reason for ban (admin tracking)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User OAuth providers: allows multiple OAuth providers per user
CREATE TABLE IF NOT EXISTS user_providers (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- 'google', 'github', 'apple', etc.
    provider_id TEXT NOT NULL,  -- The provider's unique ID for this user
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    PRIMARY KEY (provider, provider_id),
    UNIQUE (user_id, provider)  -- One entry per provider per user
);

-- User Zotero credentials: per-user Zotero API configuration
CREATE TABLE IF NOT EXISTS user_zotero_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL,  -- Zotero API key
    library_id TEXT NOT NULL,  -- Zotero library ID
    library_type TEXT DEFAULT 'user',  -- 'user' or 'group'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Notion credentials: per-user Notion OAuth access tokens
CREATE TABLE IF NOT EXISTS user_notion_credentials (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,  -- Notion OAuth access token
    bot_id TEXT,  -- Notion bot ID
    workspace_id TEXT,  -- Notion workspace ID
    workspace_name TEXT,  -- Notion workspace name for display
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User sessions: tracks active login sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,  -- Session token
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

--------------------------------------------------------------------------------
-- SUBSCRIPTIONS & BILLING
--------------------------------------------------------------------------------

-- Subscription tiers: master table defining available subscription tiers
CREATE TABLE IF NOT EXISTS subscription_tiers (
    id TEXT PRIMARY KEY,  -- 'free', 'pro', 'max'
    name TEXT NOT NULL,  -- 'Free', 'Pro', 'Max'
    display_name TEXT NOT NULL,  -- Display name for UI: 'Scholia Free', 'Scholia Pro', 'Scholia Max'
    description TEXT,  -- Description of tier benefits
    price_monthly_cents INTEGER NOT NULL,  -- Price in cents: 0, 1200, 3000
    stripe_price_id TEXT,  -- Stripe Price ID for recurring billing
    monthly_credits INTEGER NOT NULL,  -- Credits per month: 100, 800, 2400 (20× multiplier applied)
    max_rollover_credits INTEGER NOT NULL,  -- Maximum credits that can roll over
    allows_haiku BOOLEAN NOT NULL DEFAULT TRUE,  -- Whether tier includes Haiku access
    allows_flash BOOLEAN NOT NULL DEFAULT TRUE,  -- Whether tier includes Flash access
    allows_sonnet BOOLEAN NOT NULL DEFAULT FALSE,  -- Whether tier includes Sonnet access
    allows_gemini_pro BOOLEAN NOT NULL DEFAULT FALSE,  -- Whether tier includes Opus Pro access
    sort_order INTEGER NOT NULL DEFAULT 0,  -- Display order in tier list
    is_active BOOLEAN NOT NULL DEFAULT TRUE,  -- Whether tier is shown to users
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User subscriptions: tracks each user's current subscription state
CREATE TABLE IF NOT EXISTS user_subscriptions (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    tier_id TEXT NOT NULL REFERENCES subscription_tiers(id),
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'canceled', 'past_due', 'trialing'

    -- Stripe integration
    stripe_customer_id TEXT,  -- Stripe Customer ID
    stripe_subscription_id TEXT UNIQUE,  -- Stripe Subscription ID (unique for lookups)

    -- Billing cycle tracking
    current_period_start TIMESTAMPTZ,  -- Billing period start
    current_period_end TIMESTAMPTZ,  -- Billing period end
    cancel_at_period_end BOOLEAN,  -- Whether subscription will cancel at period end

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credit balances: tracks credit balance across multiple pools
CREATE TABLE IF NOT EXISTS credit_balances (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    monthly_credits INTEGER NOT NULL DEFAULT 0,  -- Current month allocation (20× multiplier)
    rollover_credits INTEGER NOT NULL DEFAULT 0,  -- Rolled over from previous month (20× multiplier)
    top_up_credits INTEGER NOT NULL DEFAULT 0,  -- Purchased credits (never expire, 20× multiplier)
    last_monthly_refresh TIMESTAMPTZ,  -- When monthly credits were last refreshed
    total_credits INTEGER,  -- Total across all pools (computed/updated for convenience)
    updated_at TIMESTAMPTZ DEFAULT NOW()  -- When balance was last updated
);

-- Credit transactions: audit log of all credit changes
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type TEXT NOT NULL,  -- 'debit', 'credit', etc.
    amount INTEGER NOT NULL,  -- Positive (credit) or negative (debit), 20× multiplier
    pool TEXT NOT NULL,  -- Which pool affected: 'monthly', 'rollover', 'top_up'
    operation_type TEXT,  -- Type of operation: 'paper_analysis', 'question', 'monthly_grant', 'subscription_grant', 'credit_purchase'
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,  -- For question transactions
    exchange_id INTEGER,  -- For question transactions (reference to conversation exchange)
    balance_after JSONB,  -- Full balance snapshot after transaction: {monthly, rollover, top_up, total}
    notes TEXT,  -- Human-readable notes about the transaction
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credit top-ups: tracks purchased credits
CREATE TABLE IF NOT EXISTS credit_top_ups (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    credits INTEGER NOT NULL,  -- Number of credits purchased (20× multiplier)
    price_cents INTEGER NOT NULL,  -- Price paid in cents
    stripe_session_id TEXT,  -- Stripe checkout session ID
    stripe_charge_id TEXT,  -- Stripe charge ID (when payment succeeds)
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'active', 'refunded', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stripe webhook events: tracks processed webhooks to prevent duplicate handling
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    id SERIAL PRIMARY KEY,
    stripe_event_id TEXT NOT NULL UNIQUE,  -- Stripe event ID for idempotency
    event_type TEXT NOT NULL,  -- Event type: 'checkout.session.completed', 'invoice.payment_succeeded', etc.
    payload JSONB NOT NULL,  -- Full webhook payload for audit/replay
    processed BOOLEAN,  -- Whether event was successfully processed
    processed_at TIMESTAMPTZ,  -- When event was processed
    error TEXT,  -- Error message if processing failed
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert subscription tiers seed data (only if not already present)
INSERT INTO subscription_tiers (
    id, name, display_name, description, price_monthly_cents, monthly_credits,
    stripe_price_id, max_rollover_credits, allows_haiku, allows_flash, allows_sonnet,
    allows_gemini_pro, sort_order, is_active
)
VALUES
    ('free', 'Free', 'Scholia Free', 'Perfect for trying Scholia with limited monthly credits',
     0, 100, NULL, 0, TRUE, TRUE, FALSE, FALSE, 1, TRUE),

    ('pro', 'Pro', 'Scholia Pro', 'For researchers who need Claude Sonnet for complex analysis',
     1200, 800, 'price_1SoWNLAyAsIPQKqiypOUYbcK', 800, TRUE, TRUE, TRUE, FALSE, 2, TRUE),

    ('max', 'Max', 'Scholia Max', 'For power users with access to Claude Opus for advanced analysis',
     3000, 2400, 'price_1SoWOOAyAsIPQKqi7xJHLnOV', 2400, TRUE, TRUE, TRUE, TRUE, 3, TRUE)
ON CONFLICT (id) DO UPDATE SET max_rollover_credits = EXCLUDED.max_rollover_credits;

--------------------------------------------------------------------------------
-- PAPER SESSIONS & ANALYSIS
--------------------------------------------------------------------------------

-- Sessions table: stores paper information and PDF location
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- Owner of this session
    filename TEXT NOT NULL,
    zotero_key TEXT,
    pdf_path TEXT NOT NULL,  -- Path to PDF file (local or Zotero)
    page_count INTEGER,  -- Number of pages in PDF (nullable for legacy sessions)
    file_size_bytes INTEGER,  -- PDF file size in bytes (nullable for legacy sessions)
    label TEXT,  -- Optional user label to distinguish multiple sessions for same paper
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table: stores chat messages between user and Claude
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    highlighted_text TEXT,  -- Optional: text highlighted by user
    page_number INTEGER,  -- Optional: page reference
    model TEXT,  -- Claude model used (e.g., 'claude-haiku-4-5', 'claude-sonnet-4-6')
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete: NULL = visible, timestamp = deleted
);

-- Flags table: user-flagged exchanges for later review
CREATE TABLE IF NOT EXISTS flags (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    note TEXT,  -- Optional user note about why flagged
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Highlights table: text selections user wants to save
CREATE TABLE IF NOT EXISTS highlights (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    page_number INTEGER,
    exchange_id INTEGER,  -- Optional: associate with conversation
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message evaluations: thumbs up/down feedback on AI responses
CREATE TABLE IF NOT EXISTS message_evaluations (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exchange_id INTEGER NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('positive', 'negative')),
    -- Reason flags (only for negative feedback)
    reason_inaccurate BOOLEAN DEFAULT FALSE,
    reason_unhelpful BOOLEAN DEFAULT FALSE,
    reason_off_topic BOOLEAN DEFAULT FALSE,
    reason_other BOOLEAN DEFAULT FALSE,
    -- Optional detailed feedback
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    -- One evaluation per exchange (can be updated)
    UNIQUE (session_id, exchange_id)
);

CREATE INDEX IF NOT EXISTS idx_evaluations_session ON message_evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_rating ON message_evaluations(rating);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON message_evaluations(created_at DESC);

-- Metadata table: extracted paper metadata
CREATE TABLE IF NOT EXISTS metadata (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT,
    authors TEXT,  -- JSON array of author names
    doi TEXT,
    arxiv_id TEXT,
    publication_date TEXT,
    journal TEXT,
    journal_abbr TEXT,  -- Journal abbreviation from Zotero
    abstract TEXT
);

-- Insights table: cached extracted insights from conversations
CREATE TABLE IF NOT EXISTS insights (
    session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    insights_json TEXT NOT NULL,  -- Full JSON blob of extracted insights
    exchange_count INTEGER NOT NULL,  -- Number of exchanges when extracted
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
    themes TEXT,  -- JSON array of existing theme names
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
    exchange_id INTEGER,  -- For queries only
    operation_type TEXT NOT NULL,  -- 'initial_analysis', 'query', 'extract_insights', 'notion_parse_context', 'notion_generate_relevance', 'notion_generate_content'
    provider TEXT NOT NULL,  -- 'claude' or 'gemini'
    model TEXT NOT NULL,
    use_thinking BOOLEAN DEFAULT FALSE,  -- Whether thinking mode was enabled
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    thinking_tokens INTEGER DEFAULT 0,  -- Thinking/reasoning tokens (Claude extended thinking, Gemini thinking)
    cache_creation_tokens INTEGER DEFAULT 0,  -- Claude only
    cache_read_tokens INTEGER DEFAULT 0,  -- Claude only
    cached_tokens INTEGER DEFAULT 0,  -- Gemini only
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User events table: tracks user activities for credit/billing purposes
CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,  -- 'paper_upload', 'question_asked', 'insights_extracted', 'notion_explored'
    metadata JSONB,  -- Flexible: {filename, exchange_id, insight_type, etc.}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

--------------------------------------------------------------------------------
-- INDEXES
--------------------------------------------------------------------------------

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_providers_user_id ON user_providers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_providers_provider_id ON user_providers(provider, provider_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_users_is_banned ON users(is_banned);

-- Session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_zotero ON sessions(zotero_key);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_exchange ON conversations(session_id, exchange_id);
CREATE INDEX IF NOT EXISTS idx_conversations_visible ON conversations(session_id, exchange_id) WHERE deleted_at IS NULL;  -- Partial index for fast visible-message lookups
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

-- Subscription and billing indexes
CREATE INDEX IF NOT EXISTS idx_subscription_tiers_active ON subscription_tiers(is_active);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_stripe_subscription ON user_subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_tier ON user_subscriptions(tier_id);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_operation ON credit_transactions(operation_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_operation ON credit_transactions(user_id, operation_type);

CREATE INDEX IF NOT EXISTS idx_credit_top_ups_user ON credit_top_ups(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_top_ups_stripe_session ON credit_top_ups(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_credit_top_ups_status ON credit_top_ups(status);

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_stripe_id ON stripe_webhook_events(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_type ON stripe_webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_processed ON stripe_webhook_events(processed);
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_created ON stripe_webhook_events(created_at DESC);

COMMIT;
