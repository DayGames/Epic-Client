# Deploying the backend to Railway (public URL)

This makes your store API reachable on the internet so the website works for anyone.

## 1. Put the code on GitHub (GitHub Desktop)

1. Open **GitHub Desktop** → **File ▸ Add local repository** → choose
   `C:\Users\Admin\Desktop\Epic Client`.
2. Click **Publish repository**. You can name it e.g. `epic-store` and keep it
   **private** (Railway can still deploy from private repos).
   - The `.gitignore` already excludes the database, uploaded files, and build output,
     so none of that gets published.

## 2. Create the Railway service

1. Go to **https://railway.app** and sign in with GitHub (free).
2. **New Project ▸ Deploy from GitHub repo** → pick the repo you just published.
3. Railway starts a build. Open the service and go to **Settings**:
   - **Root Directory**: set to `server`  ← IMPORTANT (the API lives in the `server/`
     folder; without this Railway tries to build the desktop client too and fails).
   - Railway auto-detects Python, installs `server/requirements.txt`, and runs the
     `server/Procfile` (`uvicorn main:app --host 0.0.0.0 --port $PORT`).

## 3. Set environment variables (service ▸ Variables)

| Variable       | Value                                   | Why |
|----------------|-----------------------------------------|-----|
| `SECRET_KEY`   | a long random string                    | signs login tokens — don't use the default |
| `DATABASE_URL` | `sqlite:////data/epicstore.db`          | keep the DB on a persistent volume (see step 4) |
| `FILES_DIR`    | `/data/files`                           | keep uploaded games on the volume |

(If you skip step 4, leave `DATABASE_URL`/`FILES_DIR` unset — it still works, but
uploaded games and accounts reset on every redeploy.)

## 4. (Recommended) Add a volume so data survives redeploys

1. In the service, **Settings ▸ Volumes ▸ New Volume**, mount path **`/data`**.
2. Keep the `DATABASE_URL` and `FILES_DIR` variables from step 3 (they point at `/data`).

## 5. Get your public URL

1. **Settings ▸ Networking ▸ Generate Domain**. You'll get something like
   `https://epic-store-production.up.railway.app`.
2. Test it: open `https://<your-domain>/` — you should see
   `{"status":"ok",...}`, and `https://<your-domain>/docs` for the API docs.

## 6. Point the website at it

In `Epic Store Website/index.html`, change:

```js
window.API_BASE = "https://<your-domain>";   // was http://127.0.0.1:8000
```

Then re-deploy the website (GitHub Pages / Netlify / etc.).

## Notes / limits
- Game zips are large (your Snuggle Wick is ~150 MB). Free hosting has storage and
  bandwidth limits — fine for a few games, not a big catalog.
- For a bigger store, the next step is Postgres (via Railway's Postgres plugin, set
  `DATABASE_URL` to its connection string) and object storage (S3 / Cloudflare R2) for
  the game files instead of the local `/data/files` folder.
