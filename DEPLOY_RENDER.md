# Deploying Exodus to Render (free, https, works from anywhere)

No credit card needed. Two accounts required: GitHub and Render. Total time:
~10-15 minutes.

---

## Part 1 — Put the code on GitHub

1. Go to **github.com** and sign up (or log in if you already have an account).
2. Click the **+** icon top-right → **New repository**.
3. Name it `exodus`. Leave it **Public** (simplest — Render's free tier can
   also use Private repos, but Public avoids an extra permission step).
   Don't check "Add a README". Click **Create repository**.
4. On the empty repo page, click **uploading an existing file** (a link in
   the middle of the page).
5. On your computer, open the unzipped `exodus/` folder so you can see its
   contents (`app.py`, `logic/`, `templates/`, `static/`, `data/`, etc.).
6. **Select everything inside the `exodus` folder** (not the folder itself)
   and drag it all into the GitHub upload box. Modern Chrome/Edge/Safari
   preserve the subfolders correctly when you drag multiple items at once.
7. Scroll down, click **Commit changes**.
8. Confirm on the repo page that you see `app.py`, `logic/`, `templates/`,
   `static/`, `data/`, `requirements.txt`, `DOCUMENTATION.md` at the top level
   (not nested inside an extra `exodus/` folder — if it looks nested, delete
   the repo and redo step 6, this time dragging the *contents* of the folder,
   not the folder itself).

---

## Part 2 — Deploy on Render

1. Go to **render.com** → **Get Started** → sign up with **GitHub** (this
   auto-connects your account, no separate password to manage).
2. On the Render dashboard, click **New +** → **Web Service**.
3. Find and select your `exodus` repo, click **Connect**.
4. Fill in the settings:
   - **Name**: `exodus` (this becomes part of your URL)
   - **Region**: pick the one closest to Romania (e.g. Frankfurt)
   - **Branch**: `main`
   - **Runtime**: Python 3 (should auto-detect)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: **Free**
5. Click **Create Web Service**.
6. Wait for the build/deploy log to finish (2-4 minutes). When it says
   "Live", your app is up at a URL like:
   ```
   https://exodus-xxxx.onrender.com
   ```
   (shown at the top of the page, next to your service name).

---

## Part 3 — Open it on your iPhone

1. Open Safari on your iPhone, go to your `https://...onrender.com` URL.
2. Tap **Share** → **Add to Home Screen** → **Add**.
3. You now have an Exodus icon that opens full-screen over https, from
   anywhere — no WiFi matching or computer required.

---

## Things to know

- **Free tier sleeps** after 15 minutes with no visits. The next time you
  open the app it can take 30-60 seconds to "wake up" — just wait, it's
  normal, not broken.
- **Your data lives on Render's server now**, not your computer. Render's
  free tier disks aren't guaranteed persistent across redeploys — if you
  push a code update later, your logged workouts/weights in `data/*.json`
  could reset. For now (personal use, infrequent updates) this is a fine
  tradeoff; if it becomes annoying, the fix is switching `profile_store.py`
  to a real database, which is a future upgrade, not needed today.
- **No password on it yet.** Anyone with your exact `onrender.com` link
  could open it and see your stats. The link isn't guessable, but if you
  want to lock it down, that's a small addition to `app.py` (a login prompt)
  — ask if you want that built in.
- **Updating the app later**: edit files in your GitHub repo (or push new
  ones), Render auto-redeploys within a minute or two of a new commit.

---

## Part 4 — Making a change and getting it live

Render redeploys automatically on every commit to your repo's `main`
branch — you never touch the Render dashboard for a normal update.

**A) Small edit to one file (e.g. tweak a meal idea, change a percentage)**

1. On GitHub, open the file (e.g. `logic/nutrition_engine.py`).
2. Click the **pencil icon** (top-right of the file view) to edit in the browser.
3. Make your change, scroll down, click **Commit changes** (commit directly
   to `main`).
4. Go to your Render dashboard → your service → **Events** tab. You'll see a
   new deploy start within seconds, taking 1-3 minutes.
5. Once it says **Live**, refresh the app on your phone.

**B) Replacing whole files (e.g. after I help you edit code in a session
like this one and hand you updated files)**

1. On GitHub, go to the repo → **Add file** → **Upload files**.
2. Drag in the changed file(s), keeping the same path (e.g. if
   `logic/workout_engine.py` changed, upload it so it lands at
   `logic/workout_engine.py`, not the repo root).
3. Commit. Same auto-redeploy as above.

**C) If auto-deploy doesn't seem to trigger**

Render dashboard → your service → **Manual Deploy** button (top-right) →
**Deploy latest commit**.

**Good habit before uploading:** if you're not sure a change is correct,
run `python app.py` locally first and click through the app in your own
browser — catching a typo locally takes 10 seconds, catching it after a
live deploy takes the 1-3 minute redeploy cycle each time.
