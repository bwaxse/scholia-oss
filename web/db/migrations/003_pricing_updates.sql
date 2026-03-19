-- Migration 003: Pricing updates
-- - Pro tier: 800 → 1000 credits/month (and rollover cap)
-- - Max tier: $30 → $35/month (price_monthly_cents 3000 → 3500)
--
-- NOTE: The Max stripe_price_id must be updated manually after creating a new
-- $35/month product in the Stripe dashboard (live and test mode separately).
-- Update with:
--   UPDATE subscription_tiers SET stripe_price_id = 'price_NEW_MAX_ID' WHERE id = 'max';

BEGIN;

UPDATE subscription_tiers
SET
    monthly_credits = 1000,
    max_rollover_credits = 1000
WHERE id = 'pro';

UPDATE subscription_tiers
SET
    price_monthly_cents = 3500
WHERE id = 'max';

COMMIT;
