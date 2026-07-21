"""
config.py
---------
App configuration. Reads DATABASE_URL from the environment so the exact
same code runs on:
  - your computer (defaults to a local SQLite file, zero setup)
  - Render in production (set DATABASE_URL to your free Supabase Postgres
    connection string — see SUPABASE_SETUP.md)

Nothing here needs to change between environments; only the environment
variables do.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _normalize_db_url(url):
    # Supabase/Heroku-style URLs sometimes start with postgres:// but
    # SQLAlchemy's psycopg2 driver expects postgresql://
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")

    _raw_db_url = os.environ.get("DATABASE_URL")
    if _raw_db_url:
        SQLALCHEMY_DATABASE_URI = _normalize_db_url(_raw_db_url)
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "exodus.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # pool_pre_ping: check a connection is still alive before using it. Free
    # database tiers (like Supabase's pooler) can silently drop idle
    # connections; without this, the first request after any idle period
    # would fail with a stale-connection error instead of quietly
    # reconnecting. pool_recycle forces connections to be refreshed
    # periodically for the same reason.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Set EXODUS_DEBUG=0 in production (Render env vars) to disable the
    # interactive debugger/traceback pages.
    DEBUG = os.environ.get("EXODUS_DEBUG", "1") == "1"
