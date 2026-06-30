# Tokverse Studio — Project Status & Next Steps

> **Yeh file** sab kuch ek jagah rakhti hai: kya ho chuka, kya **pending** hai, aur
> aage ka plan. Jab bhi confusion ho, pehle yeh padho.
> **Last updated:** 2026-06-30 (rich dashboard + Settings page added).

---

## 0. Live links (sab kuch kahan hai)

| Cheez | URL / naam |
|---|---|
| **Live App** (Render) | https://tokverse-studio.onrender.com |
| **Marketing site** (Vercel) | https://tokvers-studio.vercel.app |
| **GitHub repo** | github.com/imtiazai004/Tokvers-Studio (branch `main`) |
| **Render service** | `tokverse-studio` (web, **free** tier, auto-deploy ON) |
| **Database** | Neon Postgres (same DB local + prod) |
| **Storage** | Cloudflare R2 (bucket `tokverse-studio`) |
| **Queue helper** | Upstash Redis (abhi Render pe value galat — niche dekho) |

> **Naya app = `app/main.py`** (multi-tenant). Purana `main.py` (legacy) repo mein
> hai par use nahi ho raha.

---

## 1. ✅ Jo ho chuka hai (DONE)

- **Poora multi-tenant SaaS**: workspaces, auth (email/password), credits ledger,
  durable job queue (Arq), R2 storage, Neon Postgres.
- **Full pipeline** (wired): script → voice → video (per scene) → ffmpeg edit +
  captions → R2 upload → learnings. *(Keys ke baghair graceful-fail karta hai.)*
- **Providers**: video (Veo / Grok / Higgsfield) + voice (ElevenLabs / Fish) — selectable.
- **Full UI**: Create (8 video types incl. **UGC**, product-image, batch, characters,
  manual script), Dashboard, Library, Products, Learnings, Analytics, Billing, **Settings**.
- **Rich real-time Dashboard**: welcome greeting + system status, performance KPIs
  (videos/views/likes/shares/completed/credits), **real** month-over-month trend,
  live **Active Agents** panel (status from actual running jobs), recent activity +
  top videos. All wired to real data — **no dummy numbers** (zeros/idle until you generate).
- **Settings page** (real, NOT BYOK): Profile + password change, **Generation
  defaults** (pre-fill the Create form), Connections (TikTok), Plan & usage.
- **Branding**: marketing light theme + landing logo + left gradient sidebar + top action bar.
- **Billing core** (provider-agnostic): plans (Free/Starter/Pro), monthly credits,
  signup pe free credits, gateway-interface ready (Paddle/LemonSqueezy baad mein plug).
- **Hardening**: auth rate-limit, security headers, secure cookies (prod), password
  reset + email verify (console email), optional Sentry.
- **TikTok OAuth plumbing**: connect/callback/token-storage + "Connect TikTok" card
  (approval ke baad activate hoga).
- **DEPLOYED**: web-only, free tier, **LIVE** aur kaam kar raha hai (signup/login/billing/UI).
- **Marketing → App connected**: website ke Log In / Start Free Trial buttons live app pe jaate hain.

---

## 2. ⏳ Jo PENDING hai (karne ko baaki)

### 🔴 A. REDIS_URL Render pe galat hai
- **Kya:** Render ke `tokverse-shared` env group mein `REDIS_URL` ki value **kharab**
  hai (sahi `rediss://...` se shuru nahi hoti).
- **Asar abhi:** Koi nahi — app ne smart fallback kar liya (login security app ki
  apni memory pe chal rahi hai; video-queue ki abhi zaroorat nahi kyunki worker
  deploy nahi).
- **Kab theek karna zaroori:** **Worker deploy karne se pehle** (generation ke liye).
- **Fix:** Render → service → Environment → `tokverse-shared` → `REDIS_URL` edit →
  `.env` wali sahi value (jo `rediss://` se shuru hoti hai) paste → Save.

### 🟠 B. APP_BASE_URL abhi blank hai
- **Kya:** Render web service pe `APP_BASE_URL` set nahi hai.
- **Asar:** Password-reset emails mein link galat ban sakta hai. (Baaki sab theek.)
- **Fix:** Render → web service → Environment → `APP_BASE_URL` =
  `https://tokverse-studio.onrender.com` → Save.

### 🔴 C. Provider keys (sabse bada — generation iske bina nahi chalega)
- **Chahiye:** `ANTHROPIC_API_KEY` + ek video provider (`GEMINI_API_KEY` ya
  `XAI_API_KEY`) + `ELEVENLABS_API_KEY` + `DEEPGRAM_API_KEY`. Optional: Higgsfield, Fish.
- **Kahan daalna:** Render `tokverse-shared` env group.
- **Status:** ⏳ tum/client arrange kar rahe ho.

### 🟠 D. R2 48h lifecycle rule
- Cloudflare dashboard → bucket `tokverse-studio` → Settings → Object Lifecycle →
  "delete after 2 days". (Storage cost control.)

### 🟠 E. Worker deploy (generation on karne ke liye)
- `render.yaml` mein worker block **commented** hai. Keys aane pe:
  1. `REDIS_URL` theek karo (item A)
  2. `render.yaml` mein worker uncomment (needs **paid** plan)
  3. Web service pe `GENERATION_ENABLED=true`
  4. Push → generation live

### 🟡 F. Payment gateway (asli paise)
- Billing **logic** ban chuki hai, par asli gateway baaki. **Stripe Pakistan mein
  nahi chalta** → **Paddle ya LemonSqueezy** (Merchant-of-Record) plug karna hoga.
- 1 din ka kaam jab account ho — `BillingProvider` interface ready hai.

### 🟡 G. TikTok app approval
- Plumbing ready. TikTok pe developer app register + approve karwana → phir 3 env
  vars set (`TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REDIRECT_URI`).

### 🟡 H. Email (asli emails) — optional
- Abhi password-reset email sirf server log mein print hoti hai (console mode).
- Asli email bhejne ke liye: `EMAIL_PROVIDER=smtp` + `SMTP_HOST/USER/PASSWORD`
  (koi email service, e.g. Resend/SES/Gmail SMTP).

### 🟢 I. Chhoti baatein (optional)
- **Always-on:** Free instance ~15 min idle pe so jaata hai (~50s cold start).
  Paid plan (~$7/mo) se hamesha jagti rahegi. *(Abhi zaroorat nahi.)*
- **Alag prod database:** Abhi local + prod **ek hi Neon DB** use karte hain (test
  data mix hota hai). Chaaho to prod ke liye alag Neon branch banao.

---

## 3. 🗺️ Aage ka plan (order)

```
ABHI         App live + usable hai (signup/billing/UI). Kuch karna zaroori nahi.
             Chaaho to: REDIS_URL theek + APP_BASE_URL set (2 min, future-ready).

PHASE 4      KEYS aate hi:
  1) Render env group mein provider keys daalo (C)
  2) REDIS_URL theek karo (A)
  3) render.yaml mein worker uncomment + GENERATION_ENABLED=true (E)  [paid worker]
  4) R2 48h rule (D)
  5) Push -> pehla asli video banao -> cost dekho -> credit pricing set karo

PHASE 5      Payment gateway (Paddle/LemonSqueezy) plug karo (F)  -> asli bikri

PHASE 6      TikTok app approval -> 3 env vars set (G) -> auto-post + analytics

BAAD MEIN    Always-on paid plan (I), asli email SMTP (H), alag prod DB (I)
```

---

## 4. 🛠️ Common kaam kaise karein (reference)

- **Code update karke deploy:** locally change → `git add -A && git commit -m "..."`
  → `git push origin main`. Render **khud** naya version bana deta hai (~5–10 min).
- **Render pe env var add/edit:** Render → service `tokverse-studio` → **Environment**
  → group `tokverse-shared` ya service vars → edit → **Save** (auto-redeploy).
- **Live app theek chal raha hai?** kholo: `https://tokverse-studio.onrender.com/api/health`
  → `{"status":"ok","db_configured":true}` hona chahiye.
- **Error aaye to:** Render → service → **Logs** → neeche taaza error/Traceback dekho.

---

## 5. 📒 Deploy ke dauraan jo masle aaye + theek huye (history)

| Masla | Fix |
|---|---|
| `preDeployCommand` free tier pe support nahi | Hata diya; migrations `start-web.sh` mein chalti hain |
| Render card maang raha tha (Blueprint) | Card add kiya ($0 free tier) |
| GitHub repo Render ko nahi dikh raha tha | GitHub App ko repo access diya |
| Startup pe Arq/Redis crash (bad REDIS_URL) | Web startup **resilient** banaya (crash na kare) |
| DB queries 500 (galat shak — actually Redis) | Remote host ke liye SSL default-on kiya (safe improvement) |
| **Login/signup 500** — rate-limiter Redis pe crash | Rate-limiter **resilient** (bad Redis → in-memory fallback) ✅ asli fix |
| `ENCRYPTION_KEY` `.env` mein missing | Generate karke add kiya |
| Marketing buttons localhost pe ja rahe the | `web/static/config.js` APP_URL = live Render URL |

---

*Living document — har bade kaam ke baad update karna.*
