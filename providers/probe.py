"""
Viability Probe — isolates and validates the single highest-risk question:

    "Can we actually generate a usable TikTok clip with a real provider,
     and what does it cost / how long does it take?"

It needs NOTHING from the rest of the app (no DB, no queue, no web server) — just
a provider API key. Run it the moment a key is available:

    # set a key first, e.g.  XAI_API_KEY=...   or   GEMINI_API_KEY=...
    python -m providers.probe --provider grok --scenes 2
    python -m providers.probe --provider veo  --prompt "a creator unboxing a product on a cozy desk, natural light, vertical"

To get real cost numbers, also set pricing (verify the real rate):
    GROK_PRICE_PER_SECOND=...   VEO_PRICE_PER_SECOND=...
Otherwise cost is reported as "unknown" instead of a fabricated number.
"""
import argparse
import asyncio
import os
import time

from .registry import available_providers, get_provider

DEFAULT_PROMPTS = [
    "A young creator holding a skincare product to the camera in a bright bedroom, "
    "talking casually, handheld vertical 9:16, natural lighting, authentic UGC feel.",
    "Close-up of hands using a small kitchen gadget on a counter, candid home setting, "
    "vertical 9:16, soft daylight, realistic not studio.",
]


async def _run_one(provider_name, prompt, idx, duration, aspect_ratio, resolution, outdir):
    provider = get_provider(provider_name)
    out = os.path.join(outdir, f"{provider_name}_scene_{idx:02d}.mp4")
    print(f"[{provider_name}] scene {idx}: {prompt[:64]}...")
    result = await provider.generate(
        prompt, out, duration_seconds=duration,
        aspect_ratio=aspect_ratio, resolution=resolution,
    )
    size_mb = os.path.getsize(out) / 1048576 if os.path.exists(out) else 0
    cost = f"${result.cost_usd:.3f}" if result.cost_usd is not None else "unknown (set *_PRICE_PER_SECOND)"
    print(f"  ✓ {out}  [{size_mb:.1f} MB]  latency {result.latency_seconds:.1f}s  cost {cost}")
    return result


async def _main_async(args):
    prompts = [args.prompt] if args.prompt else DEFAULT_PROMPTS[: args.scenes]
    os.makedirs(args.outdir, exist_ok=True)
    started = time.monotonic()

    results = []
    for i, p in enumerate(prompts, 1):
        results.append(
            await _run_one(args.provider, p, i, args.duration,
                           args.aspect_ratio, args.resolution, args.outdir)
        )

    total = time.monotonic() - started
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    print("\n=== PROBE SUMMARY ===")
    print(f"provider     : {args.provider} ({results[0].model})")
    print(f"scenes       : {len(results)}")
    print(f"total time   : {total:.1f}s")
    if costs:
        per_scene = sum(costs) / len(costs)
        print(f"cost/scene   : ${per_scene:.3f}")
        print(f"est/video    : ${sum(costs):.2f}  (for {len(results)} scenes)")
    else:
        print("cost         : unknown — set VEO_PRICE_PER_SECOND / GROK_PRICE_PER_SECOND to measure economics")
    print("\nNow eyeball the output clips for quality before trusting the numbers.")


def main():
    ap = argparse.ArgumentParser(description="Tokverse Studio — video provider viability probe")
    ap.add_argument("--provider", required=True, choices=available_providers())
    ap.add_argument("--prompt", default=None, help="single prompt (otherwise uses built-in sample prompts)")
    ap.add_argument("--scenes", type=int, default=2, help="how many sample scenes to generate")
    ap.add_argument("--duration", type=int, default=8, help="seconds per clip")
    ap.add_argument("--aspect-ratio", default="9:16")
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--outdir", default="output/probe")
    asyncio.run(_main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
