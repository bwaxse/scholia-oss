# Changelog

All notable changes to Scholia will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- **PDF page limits enforced by subscription tier** - Free and Pro users can upload PDFs up to 20 pages; Max users up to 40 pages. Exceeding the limit returns a clear error message with a link to upgrade. Page limits are now displayed on the pricing page for each tier.

### Changed
- **Sign-up is now open to the public** - Removed the passphrase gate that previously restricted new sign-ups. A "Public Beta" badge is now displayed on the sign-up card to indicate the app's current stage.
- **Credit costs increased**: Haiku queries now cost 2 credits (up from 1), Sonnet queries now cost 8 credits (up from 4)
- **Pro tier now includes 1000 credits/month** (up from 800), with rollover cap raised to match
- **Max tier price increased to $35/month** (up from $30)
- **Top-up package prices updated**: Small $5.99 (was $4.99), Medium $24.99 (was $19.99), Large $59.99 (was $49.99)

### Fixed
- **Zotero papers now respect PDF page limits** - Page limits enforced for PDF uploads were not applied when loading papers from Zotero. Zotero-sourced papers now enforce the same per-tier page limits as direct uploads (20 pages for Free/Pro, 40 for Max).
- **Zotero picker credit label corrected** - The Zotero import button showed "Uses 1 credit" instead of the correct "Uses 20 credits" after the 20x credit system refactor.
- **Large PDF uploads now return a clear error instead of crashing** - PDFs over 32 MB are rejected before reaching the AI with a message showing the actual file size and instructions to compress. Previously, oversized files would trigger a raw Anthropic API exception that was leaked to the user.
- **Pricing page no longer advertises Claude Opus** - Removed Opus Query credit cost row from the pricing table and corrected Max tier feature description from "Best AI model (Claude Opus)" to "All AI models (Claude Sonnet, Gemini Pro)" to accurately reflect available models
- **Credit packages and costs API now returns live values** - `GET /api/credits/packages` and `GET /api/credits/costs` were previously returning stale hardcoded values that did not reflect the actual costs and prices configured in the backend; both endpoints now read dynamically from the source-of-truth constants

### Changed
- **PDF viewer mobile scroll and pinch-to-zoom fixed** - Removed custom touch handlers that conflicted with native browser gestures. Added `touch-action: pan-x pan-y pinch-zoom` so the browser handles pinch-to-zoom and scroll natively, eliminating jank on iOS and Android.
- Upgrade Claude Sonnet model from `claude-sonnet-4-5-20250929` to `claude-sonnet-4-6`
- **AI now extracts authors, journal, and year from PDFs without a DOI** - When no DOI or PMID is provided, the initial analysis prompt now instructs Claude to extract author names, journal name, and publication year directly from the paper. These are used as fallback metadata when CrossRef/PubMed are unavailable.

### Fixed
- **Fix model selector showing stale credit costs** - Model toggle buttons in the query panel were displaying pre-20x credit costs (e.g., "0.05", "0.2") instead of the correct whole-number values; Haiku now shows 2 credits and Sonnet shows 8 credits. Frontend credit checks also now use the correct costs.
- **Fix PDF text layer ghosting on macOS/Retina displays** - Text spans in the PDF viewer were bleeding through the canvas layer as faint ghost characters due to subpixel antialiasing on transparent spans, made worse by spans drifting over adjacent justified text. Fixed by clipping spans to their PDF text item width and suppressing subpixel fill color.
- **Fix letter shapes appearing during PDF text selection** - When selecting text in the PDF viewer, glyph outlines from the invisible text overlay were faintly visible over the selection highlight. Text selection color is now fully transparent so only the yellow highlight box is shown.
- **Fix ghost letters appearing above PDF text** - Removed `opacity: 0.2` from the text layer that was causing transparent text spans to become faintly visible as offset duplicates of the underlying PDF text
- **Improve PDF text highlight color visibility** - Changed text selection highlight from faint blue to yellow for much better visibility when selecting text in the PDF reader
- **Deleted and suspended users are now automatically signed out** - When any API call returns a 403 response indicating the account is deleted or suspended, the app now immediately logs the user out and redirects to the home page. Previously, these users remained in the app seeing stale anonymized data.
- **Pricing page now shows correct rollover credit amounts** - Fixed stale pre-refactor values on the pricing page; Pro now correctly shows "up to 800 rollover / 1600 total" and Max shows "up to 2400 rollover / 4800 total".
- **Subscription rollover credits now calculated correctly** - Fixed type mismatch where float values were passed to integer database columns during monthly credit rollover, which could result in incorrect credit amounts being granted.
- **Insufficient credits error on PDF upload now shows details** - When uploading a paper fails due to insufficient credits, the error message now shows how many credits are needed vs. available, with a link to top up in Settings. Previously showed a generic "Failed to create session" message.
- **Admin credit passthrough** - Admin users can now submit questions with zero credits, matching backend behavior. Enables admins to test the app, help users debug issues, and perform support tasks without needing to purchase credits.
- **Optimized Stripe webhook storage** - Removed full JSON payload (~2KB) from webhook event storage, keeping only essential metadata (`customer_id`, `subscription_id`, `invoice_id`, `amount_cents`). Achieves ~90% storage reduction per event while maintaining idempotency. Payload is never read from DB - Stripe is source of truth for full event details.

### Added
- **GDPR-compliant account deletion with soft delete + anonymization**:
  - New anonymization service implements industry best practices for user account deletion
  - **Soft delete approach**: Anonymizes PII while preserving financial/legal data
  - **What gets deleted**: User content (papers, conversations), OAuth tokens, integration credentials, personal information
  - **What gets preserved**: Financial records (subscriptions, transactions, invoices), audit trails, payment history
  - Stripe customers anonymized (not deleted) per Stripe best practices - preserves billing history for tax compliance, disputes, chargebacks
  - Database migration adds `deleted_at` and `deletion_type` columns to track account deletions
  - Auth middleware blocks deleted users from logging in
  - Admin endpoint `/api/admin/delete-user` now anonymizes instead of hard deleting
  - See `docs/stripe-integration-review.md` for detailed rationale and legal compliance requirements

### Changed
- **Stripe integration hardening**: Enhanced reliability and best practices compliance
  - Pinned Stripe API version to `2026-01-28.clover` for predictable behavior across API updates
  - Added automatic retry logic with exponential backoff for transient API failures (network issues, rate limits)
  - Retry enabled for critical operations: subscription cancellation, retrieval, checkout session retrieval
  - Replaced `delete_customer()` with `anonymize_stripe_customer()` following Stripe recommendations
  - Fixed type inconsistency in credit top-up purchases (now uses `int` consistently with 20× multiplier system)
  - Added `tenacity` library for robust retry handling

### Fixed
- **CRITICAL: Subscription upgrade credit granting now works** - Fixed webhook execution order bug where `customer.subscription.created` and `checkout.session.completed` both updated subscription details. Now only `checkout.session.completed` updates anything, allowing proper upgrade detection and credit granting in a single handler
- **CRITICAL: Subscription dates no longer regress to 1969** - Fixed regression where `subscription_created` webhook tried to update timestamps from wrong location in Stripe response. Removed all updates from that handler so dates are only set by `checkout.session.completed` which correctly extracts from `subscription.items.data[0]`
- **CRITICAL: No more duplicate subscriptions on upgrade** - Fixed `subscription_created` overwriting `stripe_subscription_id` before `checkout.session.completed` could read old ID and cancel it. Now only `checkout.session.completed` updates subscription IDs
- **CRITICAL: Account expiration dates show only when valid** - Fixed UI showing "Account expires on [past date]" from stale subscription data. Now only displays expiration warning if `cancel_at_period_end=true` AND expiration date is in the future
- **Downgrade button UX improvement** - "Downgrade" button on pricing page now opens Stripe billing portal directly instead of showing an alert, providing consistent experience with "Manage Subscription" button
- **Improved subscription webhook reliability** - Added fallback detection for old subscriptions already cancelled in Stripe (handles cases where `customer.subscription.deleted` webhook fails to fire or is delayed), prevents stale tier data when upgrading
- **Credit grant operations now robust to failures** - Added comprehensive error handling and logging around credit grants during subscription creation and upgrades, preventing silent failures and making debugging easier

### Added
- **Subscription management on Settings page**:
  - Display subscription start date and next billing date
  - Show cancellation warning when subscription is scheduled to end
  - "Upgrade to Max" button for Pro users
  - "Manage Subscription" button for all paid users (opens Stripe billing portal for payment method, billing history, cancellation)
  - API now returns `current_period_start` for billing cycle visibility

- **Tier-aware pricing page buttons**:
  - Current tier shows "Open App" button
  - Higher tiers show "Upgrade" button (with loading state)
  - Lower tiers show "Downgrade" button (directs to Settings with helpful message)
  - Unauthenticated users still see "Get Started"
  - Dynamic button labels based on subscription status

### Changed
- **BREAKING: Credit system now uses whole numbers (20× multiplier)**
  - All credit costs multiplied by 20 for clarity and to eliminate decimals
  - Credit displays now show whole numbers instead of decimals (e.g., "756" instead of "37.80")
  - Haiku/Flash queries: 0.05 → **1 credit**
  - Sonnet queries: 0.2 → **4 credits**
  - Opus queries: 0.5 → **10 credits**
  - Paper analysis: 1.0 → **20 credits**
  - Free tier: 5/month → **100/month**
  - Pro tier: 40/month → **800/month**
  - Max tier: 120/month → **2400/month**
  - **Migration**: Database automatically scaled all user balances and transaction history by 20×

### Added
- Credit rollover on subscription renewal: unused monthly and rollover credits now carry over to the next billing period (up to tier maximum)
- Admin endpoint for user account deletion with cascading removal of all associated data
- **Model restrictions for Free users**: Sonnet and Gemini Pro models now show as unavailable for free tier users with upgrade prompts, encouraging upgrades to Pro/Max tiers
- **Onboarding page for new users**: New users redirected to `/onboarding` after signup to see welcome message, account details, and available credits before accessing the app
- **Automatic free tier credits**: New users on the free tier automatically receive 5 monthly credits upon account creation (no action needed)
- **Admin-only Draft Post feature**: Draft Post button now only visible to admin users; `isAdmin` field exposed in user authentication response
- **Credit balance display in header**: Left-panel header now shows current credit balance with auto-refresh after queries
- **Inline model costs**: Model toggle buttons now display cost per use (e.g., "Sonnet 0.2") for transparent cost visibility
- **Insufficient credits modal**: Modal now appears when attempting to load a paper without sufficient credits, with clear explanation and upgrade prompts

### Fixed
- Fix subscription renewal credits not being granted due to Stripe API version change
- Fix Stripe subscription checkout webhook failing with HTTP 500 error
- Fix session creation error messages showing generic text instead of actual reason (e.g., "Insufficient credits")
- Settings page upgrade button now correctly links to pricing page
- Settings page Zotero setup button now links to Zotero integration section
- Fix credit deduction bug: Fractional credit costs (0.05 for Haiku analysis) now deduct correctly instead of rounding to 0 due to INTEGER column type
- Fix credit badge not displaying in header due to incorrect API response field name
- Fix credit breakdown values not showing decimal precision in settings page
- Fix query error messages showing "Unknown error" due to incorrect response object parsing

### Changed
- Account deletion now requires contacting support (support@scholia.fyi) instead of self-service deletion to ensure proper data handling
- **Subscription UX improved**: Upgrade buttons now on pricing page for direct checkout instead of requiring settings modal with tier selection. Simpler, more intuitive flow.
- **Credits display**: Now visible for all users (free, pro, max) with promotional messaging for free users to encourage upgrades.
- **Settings page navigation**: Section headers (Account, Zotero Integration, Notion Integration) now more visually prominent for easier scanning. Added anchor links for deep linking to specific sections.
- **Zotero setup instructions**: Now provide direct link to zotero.org/settings/security with specific guidance on finding User ID in Applications section.
- **Home page tagline**: "Read critically" now displayed as a large, prominent heading to better match the visual hierarchy of the /about page.
- **Auth page experience**: Logged-in users visiting /auth are now automatically redirected to the home page.
- **Low credit warning threshold**: Credit badge now shows warning state when balance drops below 1 credit (previously 10) for better accuracy with credit-per-query costs

### Removed
- **Think box feature**: Removed the "Think" checkbox option from chat interfaces
- Waitlist and referral system (launching with free public access for all users)
- User approval gating (all authenticated users now have immediate access)
- Upgrade modal from settings page (upgrade flow moved to pricing page)

### Added
- Multi-provider OAuth authentication (Google, GitHub)
- Notion OAuth integration for exporting insights
- LinkedIn post generation from research papers
- Session labels for organizing paper analyses
- Message evaluation system (thumbs up/down with detailed feedback)
- Usage tracking for AI token consumption
- User banning capability for admin moderation
- Notion project context caching for better export relevance
- Subscription system with Stripe integration (multiple tier management)
- Credit system with 4 pooled balance types (monthly, rollover, top-up, bonus)
- Credit enforcement on paper analysis and chat queries (model-specific costs)
- New API endpoints for subscription checkout, tier listing, credit management, and webhooks
- Frontend components for credit display, upgrade modal, and credit purchase flow

### Features
- PDF upload and text extraction (PyMuPDF)
- AI-powered paper analysis with Claude Haiku 4.5
- Interactive chat interface with Claude Sonnet 4.5
- Zotero integration for fetching paper metadata
- User-specific Zotero credentials storage
- Highlighted text selection in chat queries
- Flag important exchanges for later review
- Export insights to Notion with project context awareness
- Soft delete for conversations (preserves history)

### Infrastructure
- PostgreSQL database with 17 tables
- FastAPI backend serving REST API and static frontend
- Lit web components frontend with client-side routing
- Vite build system for frontend
- Render hosting (web service + PostgreSQL)
- Session-based authentication with httponly cookies
- CORS configuration for production domain

## Initial Release

### 2025-01-08
- Initial public release of Scholia
- Core paper analysis and chat functionality
- Zotero and Notion integrations
- OAuth authentication (Google, GitHub)
