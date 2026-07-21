# Setting up the free Supabase database (multi-user backend)

Exodus now supports real multi-user accounts, which needs a real hosted
database instead of local JSON files. Supabase's free tier gives you a
hosted Postgres database at no cost, no credit card required. This app
only uses Supabase as a **Postgres database** — it does not use Supabase
Auth, Storage, or any other Supabase service, so setup is just "create a
project, copy the connection string."

## 1. Create the project

1. Go to **supabase.com** → **Start your project** → sign up (GitHub login
   is the fastest option, and you already have a GitHub account from the
   Render deploy).
2. **New project** → pick an organization → name it `exodus` → set a
   database password (save it somewhere — you'll need it in the
   connection string) → pick a region close to Romania (e.g. Frankfurt/EU
   Central) → **Create new project**. Takes ~2 minutes to provision.

## 2. Get the connection string

1. In your project, go to **Project Settings** (gear icon) → **Database**.
2. Under **Connection string**, select the **URI** tab, and copy it. It
   looks like:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   ```
3. Replace `[YOUR-PASSWORD]` with the database password you set in step 1.
4. Use the **connection pooler** URI (the one with `pooler.supabase.com`
   and port `6543`), not the direct connection — free-tier apps on Render
   work better through the pooler.

## 3. Set it as your app's DATABASE_URL

**Locally** (optional — SQLite works fine for local dev, this is only
needed for testing against the real production database):
```
export DATABASE_URL="postgresql://...your connection string..."
python app.py
```

**On Render** (this is the one that matters for your live app):
1. Render dashboard → your `exodus` service → **Environment** tab.
2. **Add Environment Variable**: key `DATABASE_URL`, value = your
   Supabase connection string.
3. Save — Render redeploys automatically with the new database.

That's it — no code changes. `config.py` already reads `DATABASE_URL` and
falls back to local SQLite when it's not set, so the exact same code works
in both places (see `config.py` and `app.py`).

## 4. First boot creates and seeds the tables automatically

`app.py` calls `db.create_all()` and the seed functions in `logic/seed.py`
every time the app starts. The first request after you set `DATABASE_URL`
will create all the tables in your new Supabase database and load the
exercise/meal/food/CrossFit libraries into it. You'll see them under
**Table Editor** in the Supabase dashboard afterward.

## Free tier limits to know about

- **500MB database** — enormous headroom for a personal/small-group app;
  you'd need years of daily logging by many users to get close.
- **Projects pause after 1 week of no API activity** on the free tier —
  opening the app wakes it back up within a few seconds, no data lost.
- **No credit card required** for the free tier as of this writing.

## Rolling back to local-only

If you ever want to go back to the simple local SQLite setup, just remove
the `DATABASE_URL` environment variable (locally: `unset DATABASE_URL`; on
Render: delete the env var and redeploy). Nothing else changes.
