# Tokverse Studio — Marketing Site (Vercel)

This folder is the **static marketing website**. It is fully self-contained
(plain HTML/CSS/JS, no backend) and is meant to be deployed to **Vercel** (or any
static host). The actual application — login, dashboard, video generation,
purchasing, downloads — runs separately as the **FastAPI app on Render**.

```
Visitor ─▶ Vercel (this folder, www.<domain>)
              │  "Start Free Trial" / "Log In" / "Create Video"
              ▼
           Render app (app.<domain>)  ── login, generate, download, billing
              │  large videos
              ▼
           Cloudflare R2 + CDN (optional, see below)
```

## How the seamless link-up works

The marketing site never talks to the backend directly. Instead, every
app-bound link (Start Free Trial, Log In, Create Video, Dashboard, Analytics)
is rewritten at page load to point at the application origin.

- `static/config.js` defines `window.APP_URL` — the app origin.
- `static/components/app-links.js` rewrites app links to `APP_URL + path`.

So login / signup / purchasing / download keep working exactly like before —
they just open on the app's own domain. Visitors experience one continuous product.

### Set the app URL
Edit **`static/config.js`**:

```js
// Local dev (FastAPI running on your machine)
window.APP_URL = "http://localhost:8000";

// Production (after Render domain is set)
window.APP_URL = "https://app.your-domain.com";
```

## Deploy to Vercel

1. Push the repo to GitHub (or use the Vercel CLI).
2. In Vercel → **New Project** → import the repo.
3. Set **Root Directory** to `web`.
4. Framework preset: **Other** (no build step — static).
5. Build command: *(leave empty)* · Output directory: *(leave empty / `.`)*
6. Deploy. `vercel.json` enables clean URLs (`/features`, `/pricing`) and caching.

CLI alternative:
```bash
cd web
vercel --prod
```

## Deploy the app to Render

The app stays as-is (this repo's root `Dockerfile` + `main.py`). It already
deploys via `render.yaml`. After it's live, note its URL (e.g.
`https://tokverse-studio.onrender.com`) and either:

- use it directly as `APP_URL`, **or**
- map a subdomain `app.your-domain.com` to the Render service (Render →
  Settings → Custom Domains), then set `APP_URL = https://app.your-domain.com`.

### Domains (recommended, for the seamless feel)
- `www.your-domain.com` (and apex) → **Vercel** (this marketing site)
- `app.your-domain.com` → **Render** (the application)

## Videos on Cloudflare R2 (optional, recommended for speed)

The large `static/videos/*.mp4` and `static/hero.mp4` are the heaviest assets.
For best performance, store them on **Cloudflare R2** (zero egress fees) behind
the CDN, and point the `<video src=...>` tags at the R2/CDN URL. Until then they
serve fine from Vercel. Compress 8K masters to 1080p/1440p WebM/MP4 first
(ffmpeg) — visitors won't see a difference, load time drops sharply.

## Notes / follow-ups
- This folder is a **copy** of the marketing files from `../static/`. The root
  FastAPI app still serves the marketing pages too, so local dev is unaffected.
  Once the Vercel deploy is validated, the marketing routes/files can be removed
  from the FastAPI app so there is a single source of truth.
- `login.html` / `signup.html` belong to the **app** (they call `/api/auth/*`),
  so they stay on Render — not in this folder.
