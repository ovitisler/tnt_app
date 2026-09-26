# Deploying to Vercel

## Prerequisites
- GitHub account with the repo pushed
- Vercel account connected to GitHub
- Google Sheets service account credentials

## First-time Setup

1. **Import the project in Vercel**
   - New Project → import `ovitisler/tnt_app`
   - Framework: Other
   - Build command: *(leave blank)*
   - Output directory: *(leave blank)*

2. **Set environment variables** (Vercel dashboard → Settings → Environment Variables)

   | Variable | Value |
   |---|---|
   | `GOOGLE_SHEETS_CREDS` | Full contents of `client_secret.json` |
   | `SHEET_NAME` | Your Google Sheet name (e.g. `TNT_App_Data`) |
   | `CACHE_BACKEND` | `redis` (recommended) or `memory` |

3. **Set up Redis** (if using `CACHE_BACKEND=redis`)
   - Vercel dashboard → Storage → Create → Redis
   - Connect it to the project — this auto-adds `REDIS_URL`

4. **Deploy** — Vercel deploys automatically on every push to `main`

## Caching

| `CACHE_BACKEND` | Behavior |
|---|---|
| `memory` | In-process dict. Fast, but cache is per-instance and lost on cold start. Default. |
| `redis` | Vercel Redis. Shared across all serverless instances. Survives cold starts. Recommended for production. |

Cache TTLs:
- Static sheets (Schedule, Roster, Book Sections): 24 hours
- Dynamic sheets (Completed Sections, Attendance): 15 seconds

To flush the cache manually: `GET /test/cache/clear`

## Updating

Push to `main` — Vercel redeploys automatically. No build step needed.

## Pushing from local

The remote requires a GitHub PAT:

```bash
git push https://ovitisler:<PAT>@github.com/ovitisler/tnt_app.git main
```
