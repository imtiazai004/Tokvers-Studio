# providers/ — video generation abstraction + viability probe

One provider-neutral interface (`VideoProvider`) with adapters per backend. The app
talks only to the interface; adding/swapping a provider = one adapter.

| File | Role |
|---|---|
| `base.py` | `VideoProvider` interface + `GenerationResult` |
| `veo.py` | Veo 3 adapter (Google Gemini API, verified contract) |
| `grok.py` | Grok Imagine adapter (xAI, verified contract) |
| `registry.py` | `get_provider("veo"\|"grok")` factory |
| `settings.py` | env-driven keys / model ids / pricing |
| `probe.py` | viability probe (run when a key is available) |

## Run the viability probe (Step 0)

Needs only a provider API key — no DB, queue, or server.

```bash
# Grok Imagine (xAI)
export XAI_API_KEY=...                 # PowerShell: $env:XAI_API_KEY="..."
python -m providers.probe --provider grok --scenes 2

# Veo 3 (Google Gemini API)
export GEMINI_API_KEY=...
python -m providers.probe --provider veo --scenes 2
```

Optional — real cost numbers (verify the true per-second rate first):
```bash
export GROK_PRICE_PER_SECOND=...
export VEO_PRICE_PER_SECOND=...
```

Output clips land in `output/probe/`. Eyeball them for quality, read the printed
latency/cost. This validates the core (quality + economics) before any further
SaaS infrastructure is built around it.

## Env vars
| Var | Purpose |
|---|---|
| `VEO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_AI_STUDIO_API_KEY` | Veo key (first found wins) |
| `VEO_MODEL` | default `veo-3.1-generate-preview` |
| `XAI_API_KEY` / `GROK_API_KEY` | Grok key |
| `GROK_MODEL` | default `grok-imagine-video` |
| `VEO_PRICE_PER_SECOND` / `GROK_PRICE_PER_SECOND` | optional, for real cost |
