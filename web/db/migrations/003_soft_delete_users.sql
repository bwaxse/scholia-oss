-- Migration 003: Add soft delete support for users
-- Implements GDPR-compliant account deletion with data retention for legal compliance

BEGIN;

-- Add soft delete columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deletion_type TEXT;

-- Create index for deleted users (for filtering active users)
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at) WHERE deleted_at IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN users.deleted_at IS 'Timestamp when user account was deleted/anonymized (NULL = active account)';
COMMENT ON COLUMN users.deletion_type IS 'Type of deletion: user_requested, admin_deleted, gdpr_request';

COMMIT;
