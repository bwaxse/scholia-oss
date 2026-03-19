# Stripe Go-Live Checklist

## Step 1 — Create live products in Stripe Dashboard

Switch to **Live mode** in the Stripe dashboard and create two recurring products:
- **Scholia Pro** — $12/month → note the `price_xxx` ID
- **Scholia Max** — $35/month → note the `price_xxx` ID

Also recreate any one-time top-up products if you have them.

---

## Step 2 — Update price IDs in production database

The price IDs currently in the DB are test-mode prices and won't work with live keys. Run this against the production Postgres after deploy:

```sql
UPDATE subscription_tiers
SET stripe_price_id = 'price_LIVE_PRO_ID_HERE'
WHERE id = 'pro';

UPDATE subscription_tiers
SET stripe_price_id = 'price_LIVE_MAX_ID_HERE'
WHERE id = 'max';
```

---

## Step 3 — Update env vars on Render

| Variable | Where to find it |
|----------|-----------------|
| `STRIPE_SECRET_KEY` | Stripe → Developers → API keys → Secret key (live) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe → Developers → API keys → Publishable key (live) |
| `STRIPE_WEBHOOK_SECRET` | From Step 4 below |
| `STRIPE_BILLING_PORTAL_CONFIGURATION_ID` | From Step 5 below |

---

## Step 4 — Register the live webhook

In the Stripe dashboard (live mode):
- Go to **Developers → Webhooks → Add endpoint**
- URL: `https://scholia.fyi/api/webhooks/stripe`
- Events to listen for:
  - `checkout.session.completed`
  - `invoice.payment_succeeded`
  - `customer.subscription.deleted`
- After saving, reveal the **Signing secret** → set as `STRIPE_WEBHOOK_SECRET`

---

## Step 5 — Configure the Customer Portal

In Stripe dashboard (live mode) → **Settings → Billing → Customer portal**:
- Enable it and configure what customers can do (cancel, update payment method, etc.)
- Copy the **Configuration ID** (starts with `bpc_`) → set as `STRIPE_BILLING_PORTAL_CONFIGURATION_ID`

---

## Step 6 — Deploy & smoke test

1. Create a real account on scholia.fyi
2. Subscribe with a real card (use a small amount if preferred, then refund via Stripe dashboard)
3. Verify credits are granted, the portal works, and cancellation works

---

# Done 3/9/26