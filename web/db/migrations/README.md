# Database Migrations

This directory contains SQL migration scripts for the Scholia production database.

## Running Migrations on Render

### Option 1: Using Render Shell (Recommended)

1. Go to your Render dashboard
2. Navigate to your PostgreSQL database
3. Click "Connect" → "External Connection"
4. Use the provided PSQL command to connect:
   ```bash
   PGPASSWORD=<password> psql -h <host> -U <user> <database>
   ```

5. Once connected, run the migration:
   ```sql
   \i /path/to/migration.sql
   ```

### Option 2: Using psql from Local Machine

1. Get your `DATABASE_URL` from Render environment variables
2. Run the migration:
   ```bash
   psql "postgresql://user:password@host:port/database" -f migrations/001_add_session_label.sql
   ```

### Option 3: Copy-Paste in Render SQL Editor

1. Go to Render Dashboard → Your PostgreSQL Database
2. Open the "Query" tab
3. Copy the contents of the migration file
4. Paste and execute

## Migration History

| Migration | Date | Description |
|-----------|------|-------------|
| 001_add_session_label.sql | 2026-01-02 | Add optional label column to sessions table |

## Creating New Migrations

1. Create a new file with format: `NNN_description.sql`
2. Use `IF NOT EXISTS` or `IF EXISTS` clauses to make migrations idempotent
3. Test on local database first
4. Document in this README
5. Apply to production via one of the methods above
