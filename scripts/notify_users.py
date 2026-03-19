"""
Scholia shutdown notification script.

Connects to production DATABASE_URL, queries active users,
and outputs a CSV of emails + names. Use this to send the
shutdown/open-source notification email manually.

Usage:
    DATABASE_URL=postgresql://... python scripts/notify_users.py
    # or with .env:
    python scripts/notify_users.py
"""

import asyncio
import csv
import os
import sys

import asyncpg
from dotenv import load_dotenv

load_dotenv()

EMAIL_TEMPLATE = """
Subject: Scholia is going open source

Hi {name},

Scholia is transitioning to an open-source project. The hosted version at
scholia.fyi will be shutting down this week.

The good news: Scholia is now available as a free, open-source tool you can
run locally with your own API key. Get started here:
https://github.com/bwaxse/scholia-oss

If you'd like a copy of your data (conversations, highlights, etc.), reply
to this email and I'll export it for you.

Thanks for being an early user!

Bennett
"""


async def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set.", file=sys.stderr)
        sys.exit(1)

    # asyncpg requires postgresql:// not postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    print(f"Connecting to database...", file=sys.stderr)
    conn = await asyncpg.connect(database_url)

    try:
        rows = await conn.fetch(
            """
            SELECT email, name
            FROM users
            WHERE deleted_at IS NULL
              AND is_banned = FALSE
            ORDER BY created_at ASC
            """
        )
    finally:
        await conn.close()

    print(f"Found {len(rows)} active users.", file=sys.stderr)
    print("", file=sys.stderr)
    print("--- EMAIL TEMPLATE ---", file=sys.stderr)
    print(EMAIL_TEMPLATE, file=sys.stderr)
    print("--- USER CSV ---", file=sys.stderr)

    writer = csv.writer(sys.stdout)
    writer.writerow(["email", "name"])
    for row in rows:
        writer.writerow([row["email"], row["name"]])


if __name__ == "__main__":
    asyncio.run(main())
