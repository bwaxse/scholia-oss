-- Optimize Stripe webhook storage by removing full payload and storing only essential metadata
-- Reason: Full ~2KB JSON payload is never read from database, only idempotency check is needed
-- Expected storage savings: ~90% (2KB → ~200 bytes per event)

BEGIN;

-- Add metadata columns for common queries and debugging
ALTER TABLE stripe_webhook_events
ADD COLUMN IF NOT EXISTS customer_id TEXT,
ADD COLUMN IF NOT EXISTS subscription_id TEXT,
ADD COLUMN IF NOT EXISTS invoice_id TEXT,
ADD COLUMN IF NOT EXISTS amount_cents INTEGER;

-- Drop the unused payload column (saves ~90% storage per row)
ALTER TABLE stripe_webhook_events
DROP COLUMN IF EXISTS payload;

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_customer_id
ON stripe_webhook_events(customer_id) WHERE customer_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_stripe_webhook_events_subscription_id
ON stripe_webhook_events(subscription_id) WHERE subscription_id IS NOT NULL;

COMMIT;
