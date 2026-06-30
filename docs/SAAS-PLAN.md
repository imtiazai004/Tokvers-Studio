# Tokverse Studio — SaaS Plan (Reality + Roadmap)

> Yeh living document batata hai app **abhi kahan khadi hai**, **kya ban chuka hai**,
> aur launch tak **kya-kya baaki hai (kis order mein)**.
> **Last revised:** 2026-06-30.

---

## 1. Ek line mein khulasa

Pehle yeh ek single-person tool tha. **Ab yeh ek asli multi-tenant SaaS hai** —
workspace-based data isolation, credit billing ledger, durable job queue, managed
Postgres, object storage, aur **sahi video-provider integrations** sab ban chuke
hain. Poori product UI bhi tayyar hai (create, characters, dashboard, library,
products, learnings, analytics) aur marketing brand ke theme/logo se match karti hai.
**Jo baaki hai woh "neev" nahi — woh activation (keys), paisa (Stripe), aur
integrations (TikTok) + hardening/deploy hai.**

---

## 2. Architecture (LOCKED)

| Layer | Choice |
|---|---|
| Marketing site | Static on **Vercel** ✅ live |
| App backend | **FastAPI** (async), `app/main.py` |
| Database | **Neon Postgres** (async SQLAlchemy 2.0 + asyncpg) |
| Jobs | **Arq + Redis (Upstash)**, alag worker process |
| Storage | **Cloudflare R2** (aioboto3) + signed URLs, 48h retention |
| Billing model | **Credits** (usage-based ledger: hold → settle/refund) |
| Multi-tenancy | **workspace_id** har tenant row pe |
| Video AI | **Veo (Gemini API) / Grok Imagine / Higgsfield** (selectable) |
| Voice AI | **ElevenLabs / Fish Audio** (selectable) |
| Captions | **Deepgram API** (BYOK key) |
| Script AI | **AsyncAnthropic** (Claude) |
| Keys model | **Platform-owned** (BYOK nahi) — user credits se pay karta hai |

---

## 3. Kya ban chuka hai (DONE)

### 🟢 Foundation (purana Phase 0–2 — sab complete)
| Cheez | Halat |
|---|---|
| Multi-tenancy (User + Workspace + Membership, har query scoped) | ✅ |
| Neon Postgres + async engine + Alembic-ready models (11 tables) | ✅ |
| Credit ledger: `get_balance / add / charge / hold / settle / refund` + cap + kill-switch | ✅ |
| Durable jobs: Arq worker, job status DB mein, live progress, retry/refund on fail | ✅ |
| R2 storage: upload/download/signed-url/delete + lifecycle helper | ✅ |
| Persistent secrets (`ENCRYPTION_KEY`, `SESSION_SECRET`), Fernet encrypt | ✅ |
| Auth: email/password (bcrypt) + sessions, signup banaye User+Workspace | ✅ |

### 🟢 Core pipeline (purana Phase 3 — complete)
| Cheez | Halat |
|---|---|
| Video providers **sahi** endpoint/model/schema pe (Veo `predictLongRunning`, Grok `grok-imagine-video`) | ✅ |
| Voice providers (ElevenLabs + Fish) abstraction | ✅ |
| Full pipeline: script → voiceover → per-scene clips → ffmpeg edit (merge+voice+captions) → R2 upload | ✅ |
| AsyncAnthropic (non-blocking LLM calls) | ✅ |
| Learnings: winning hook / preferred tool / top hashtags auto-record | ✅ |
| Graceful-fail bina keys (hold → fail → auto-refund), keys aate hi instantly active | ✅ |

### 🟢 Product UI (feature-parity — complete)
| Page / feature | Halat |
|---|---|
| Create (topic, niche, **8 video types incl. UGC**, provider, voice, character, product-image→video, manual script, batch, scenes) | ✅ |
| Live **agents pipeline** strip (script→voice→video→edit→store) | ✅ |
| Characters (consistent recurring face across scenes) | ✅ |
| Dashboard (KPIs + recent jobs) | ✅ |
| Library (R2 signed-URL playback) | ✅ |
| Products (per-product performance rollup) | ✅ |
| Learnings (agent learnings + script patterns) | ✅ |
| Analytics (totals + manual per-video metric tracking) | ✅ |
| **Branding:** marketing light theme + landing logo (spinning icon + gradient wordmark) + left brand-gradient sidebar + top action bar | ✅ |

---

## 4. Kya baaki hai (TODO) — yahi ab kaam hai

### 🔴 4.1 Activation — provider keys (USER pe blocked)
- **Kya:** `.env` mein keys daalni hain — Anthropic, Veo/Grok (jo use karna ho),
  ElevenLabs, Deepgram (captions). Optional: Higgsfield, Fish.
- **Kyun:** Bina keys app graceful-fail karti hai (refund). Keys aate hi asli
  generation chalu.
- **Status:** ⏳ **User action** — keys arrange karna.

### 🔴 4.2 R2 48h lifecycle rule (USER pe blocked)
- **Kya:** Cloudflare dashboard → Bucket `tokverse-studio` → Settings → Object
  Lifecycle Rules → "delete after 2 days".
- **Kyun:** Storage cost control; DB record rehta hai, sirf file delete.
- **Status:** ⏳ **User action** (object-scoped token API se set nahi kar sakta).

### 🟠 4.3 Real generation test + pricing calibration
- Ek real key se **ek video end-to-end** generate karke quality dekho.
- Asli **cost per video** measure karo (Veo + voice + Claude + Deepgram).
- Us cost ke hisaab se **per-provider credit pricing** set karo (`providers/settings.py`).
- **Status:** keys ke baad turant.

### 🟠 4.4 Stripe billing (paisa)
- Abhi dev "+ Add 50" test top-up hai. Isko **Stripe** subscription/checkout se replace.
- Plan tiers (e.g. Starter/Pro) + per-plan **monthly credit quota** + usage metering.
- Webhooks se credits top-up; failed payment handling.
- **Status:** key-independent — abhi shuru ho sakta hai.

### 🟠 4.5 TikTok OAuth (real integration)
- Official **Login Kit + Content Posting API** (password scraping nahi).
- Analytics pull (views/likes/shares auto, abhi manual hai) + optional auto-post.
- **Note:** TikTok app approval lagega — parallel mein apply karna.
- **Status:** key/approval pe depend.

### 🔵 4.6 Hardening (launch se pehle)
- Auth rate-limit (brute-force), email verification, password reset.
- Secure cookies (`https_only`), CSRF, input validation review.
- Error tracking (Sentry), structured logging.
- **Security backlog:** Neon password **rotate** karna (chat mein expose hua tha).
- **Status:** deploy se pehle.

### 🔵 4.7 Deploy + legacy cutover
- Render pe: **web** service (`app/main.py`) + alag **worker** (`arq worker.WorkerSettings`).
- Entrypoint legacy `main.py` (port 8000) se naye `app/main.py` pe switch.
- Purana code (Selenium scraper, toote provider tools, legacy `settings.html`/`guide.html`) retire.
- **Status:** hardening ke saath.

---

## 5. Revised roadmap (remaining order)

```
✅ Phase 0  Foundation (multi-tenancy, Postgres, secrets)      — DONE
✅ Phase 1  Storage (R2 + signed URLs)                          — DONE
✅ Phase 2  Durable jobs (Arq + Redis worker)                   — DONE
✅ Phase 3  Video providers fix + async + full pipeline         — DONE
✅ Phase 3b Full product UI + feature parity + branding         — DONE
⏳ Phase 4  ACTIVATION  → keys (.env) + R2 lifecycle + 1 real run + pricing
⬜ Phase 5  MONETIZATION → Stripe subscriptions + plan quotas
⬜ Phase 6  INTEGRATIONS → TikTok OAuth (analytics + posting)
⬜ Phase 7  HARDENING + DEPLOY → security, Sentry, Render, legacy cutover
```

---

## 6. User pe abhi kya pending hai (do cheezein)

1. **Provider keys** `.env` mein daalna (Anthropic + ek video provider + ElevenLabs + Deepgram minimum).
2. **R2 48h lifecycle rule** Cloudflare dashboard mein set karna.

> In dono ke baghair baaki sab build/test ho chuka hai — yeh sirf "switch on" karte hain.

---

## 7. Recommended next step

**Do raaste, parallel ho sakte hain:**

- **Agar keys ready hain →** Phase 4: ek real generation chala kar quality/cost dekho,
  phir pricing set karo. (Sabse zyada confidence yahin milega — product actually
  kaam karta dikhega.)
- **Agar keys abhi nahi →** Phase 5 (Stripe billing) **key-independent** hai, abhi
  shuru kar sakte hain — taa-ke keys aate hi product bik-ne ke liye tayyar ho.

**Meri sifarish:** keys arrange karte hue, main **Stripe billing (Phase 5)** shuru
kar du — yeh blocked nahi hai aur "paying SaaS" banne ka agla bada step hai.

---

*Living document — har phase ke saath update hota rahega.*
